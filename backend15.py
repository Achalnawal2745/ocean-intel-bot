# requirements.txt
"""
fastapi==0.104.1
uvicorn==0.24.0
asyncpg==0.29.0
google-generativeai==0.3.2
chromadb==0.4.18
plotly==5.17.0
pandas==2.1.3
numpy==1.25.2
supabase==2.3.1
sentence-transformers==2.2.2
"""

# backend13.py - COMPREHENSIVE AI-FIRST 3-LAYER SYSTEM
import os
import re
import asyncio
import logging
import json
import uuid
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List, Tuple
from contextlib import asynccontextmanager
from collections import defaultdict

import asyncpg
import chromadb
import google.generativeai as genai
import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from chromadb.utils import embedding_functions
from supabase import create_client, Client

# ==================== CONFIGURATION ====================
DATABASE_URL = "postgresql://postgres.locaacxacuphdlfautru:nawal12345@aws-1-ap-south-1.pooler.supabase.com:6543/postgres"
GEMINI_API_KEY = "AIzaSyDsXC0MFD93Ri-UHLVitl5KLQGtdCPdfMc"
SUPABASE_URL = "https://locaacxacuphdlfautru.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxvY2FhY3hhY3VwaGRsZmF1dHJ1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTcyMjMxNTksImV4cCI6MjA3Mjc5OTE1OX0.KDBXCTWWtxqseTpZk3IIMpnszBPWk7yqT1gR192nLA4"

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Extended regions with proper bounding boxes
REGIONS = {
    "equator": (-5, 5, -180, 180),
    "arabian_sea": (5, 25, 50, 75),
    "indian_ocean": (-40, 25, 40, 120),
    "bay_of_bengal": (5, 22, 80, 95),
    "south_atlantic": (-40, 0, -50, 20),
    "north_pacific": (0, 60, 120, -120),
}

# ==================== SQL GENERATION SYSTEM ====================
class SQLGenerationSystem:
    def __init__(self, gemini_model, supabase_client, db_pool=None):
        self.gemini_model = gemini_model
        self.supabase = supabase_client
        self.db_pool = db_pool
        
    def _get_sql_generation_prompt(self) -> str:
        return '''
        You are an AI assistant specialized in Argo float data. You were made by the Thapar University Team of FloatChat AI.
        Your task is to understand user queries and either:

        1. Generate an SQL query to retrieve data, or  
        2. Provide a textual explanation, or
        3. Provide a graph (1D, 2D, or heatmap), or
        4. Provide both textual explanation and graph.

        Database Schema:

        - float_metadata(
            PLATFORM_NUMBER, FLOAT_SERIAL_NUMBER, LAUNCH_DATE, LAUNCH_LATITUDE, LAUNCH_LONGITUDE, 
            PI_NAME, PROJECT_NAME, OPERATING_INSTITUTE, START_DATE, END_OF_LIFE, FIRMWARE_VERSION,
            DEPLOYMENT_PLATFORM, FLOAT_OWNER
        )
        - profiles(
            FLOAT_ID, CYCLE_NUMBER, PROFILE_DATE, LATITUDE, LONGITUDE, DIRECTION, MAX_DEPTH, N_LEVELS
        )
        - measurements(
            FLOAT_ID, CYCLE_NUMBER, N_LEVEL, PRESSURE, DEPTH_M, TEMPERATURE, SALINITY
        )

        COLUMN NOTES:
        - Use TEMPERATURE (not TEMP)
        - Use SALINITY (not PSAL) 
        - PRESSURE is in dbar (depth equivalent)
        - DEPTH_M is actual depth in meters

        Rules:

        1. Always respond in a JSON array with a single object: 
        [
          {
            "SQL": "",
            "TEXT": "",
            "GRAPHS": {},
            "CONTEXT": []
          }
        ]

        2. *SQL Queries*:
           - Fill the SQL field only when a query is needed.
           - TEXT and GRAPHS must be empty in this case.
           - SQL must use columns from the schema.
           - Always include LIMIT for safety.

        3. *Text + Graphs*:
           - TEXT contains natural language explanation.
           - GRAPHS is optional.

        4. *Context Generation*:
           - CONTEXT array should include any parameters mentioned.

        Examples:

        ### SQL QUERY
        [
          {
            "SQL": "SELECT TEMPERATURE, SALINITY FROM measurements WHERE FLOAT_ID = 2901456 AND ABS(PRESSURE - 500) <= 10 LIMIT 100;",
            "TEXT": "",
            "GRAPHS": {},
            "CONTEXT": []
          }
        ]

        ### Text Only
        [
          {
            "SQL": "",
            "TEXT": "The temperature at 500m depth for float 2901456 is approximately 4.2°C and salinity is 35 PSU.",
            "GRAPHS": {},
            "CONTEXT": ["float 2901456", "depth 500 meters", "temp 4.2°C", "salinity 35 PSU"]
          }
        ]
        '''
    
    async def generate_sql_response(self, query: str, context: dict) -> Dict[str, Any]:
        """Generate SQL or appropriate response using Gemini"""
        try:
            user_data = [{
                "USER_QUERY": query,
                "RETRIEVED_CONTEXT": context,
                "PREVIOUS_CONVERSATION_CONTEXT": [],
                "SQL_DATA": ""
            }]
            
            final_prompt = f"{self._get_sql_generation_prompt()}\n\n### Actual Data for this Query:\n{user_data}"
            
            response = await asyncio.to_thread(
                lambda: self.gemini_model.generate_content(final_prompt)
            )
            
            response_text = response.text.strip()
            response_text = response_text.replace('```json', '').replace('```', '').strip()
            
            response_json = json.loads(response_text)
            result = response_json[0] if isinstance(response_json, list) else response_json
            
            logger.info(f"SQL Generation Result: {result}")
            
            # If SQL is generated, execute it
            if result.get('SQL') and result['SQL'].strip():
                sql_query = result['SQL'].strip()
                if 'LIMIT' not in sql_query.upper():
                    sql_query = sql_query.replace(';', '') + ' LIMIT 100'
                
                logger.info(f"Executing generated SQL: {sql_query}")
                # Try direct database query first
                if self.db_pool:
                    try:
                        async with self.db_pool.acquire() as conn:
                            rows = await conn.fetch(sql_query)
                            data = [dict(row) for row in rows]
                            return {
                                "success": True,
                                "data": data,
                                "sql_query": sql_query,
                                "text_response": result.get('TEXT', ''),
                                "graphs": result.get('GRAPHS', {}),
                                "context": result.get('CONTEXT', []),
                                "source": "sql_generation",
                                "data_count": len(data)
                            }
                    except Exception as e:
                        logger.error(f"Direct SQL query failed: {e}")

                # Fallback to Supabase RPC if direct query failed or no pool
                try:
                    sql_response = self.supabase.rpc("execute_sql_query", {"query": sql_query}).execute()
                    
                    if sql_response.data and len(sql_response.data) > 0:
                        return {
                            "success": True,
                            "data": sql_response.data,
                            "sql_query": sql_query,
                            "text_response": result.get('TEXT', ''),
                            "graphs": result.get('GRAPHS', {}),
                            "context": result.get('CONTEXT', []),
                            "source": "sql_generation",
                            "data_count": len(sql_response.data)
                        }
                except Exception as e:
                    logger.error(f"Supabase RPC query failed: {e}")
                    return {
                        "success": False,
                        "error": f"Query execution failed: {str(e)}",
                        "source": "sql_generation"
                    }
                else:
                    return {
                        "success": False,
                        "error": "No data found for the generated SQL query",
                        "sql_query": sql_query,
                        "text_response": result.get('TEXT', 'Sorry, no data available for this query.'),
                        "source": "sql_generation"
                    }
            else:
                return {
                    "success": True,
                    "text_response": result.get('TEXT', 'I understand your query but no specific data retrieval was needed.'),
                    "graphs": result.get('GRAPHS', {}),
                    "context": result.get('CONTEXT', []),
                    "source": "text_response"
                }
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in SQL generation: {e}")
            return {
                "success": False,
                "error": "Failed to parse AI response",
                "text_response": "I encountered an error processing your query. Please try again.",
                "source": "sql_generation"
            }
        except Exception as e:
            logger.error(f"SQL generation failed: {e}")
            return {
                "success": False,
                "error": f"SQL generation failed: {str(e)}",
                "source": "sql_generation"
            }

# ==================== DATA FORMATTER ====================
class DataFormatter:
    @staticmethod
    def format_depth_profile_data(data: List[Dict], parameter: str = "temperature", float_id: Optional[int] = None) -> Dict[str, Any]:
        """Format depth profile data for frontend plotting"""
        if not data:
            return {"error": "No data available"}
            
        # Use pressure for depth (as per your CSV structure)
        depths = [item.get('pressure') for item in data if item.get('pressure') is not None]
        values = [item.get(parameter) for item in data if item.get(parameter) is not None]
        
        if not depths or not values:
            return {"error": f"No {parameter} data available"}
            
        return {
            "type": "depth_profile",
            "float_id": float_id,
            "parameter": parameter,
            "data": {
                "depths": depths,
                "values": values
            },
            "metadata": {
                "units": {
                    "depth": "dbar",
                    "parameter": "°C" if parameter == "temperature" else "PSU" if parameter == "salinity" else "dbar"
                },
                "data_points": len(depths),
                "parameter_name": parameter.capitalize()
            }
        }
    
    @staticmethod
    def format_trajectory_data(data: List[Dict]) -> Dict[str, Any]:
        """Format trajectory data for frontend mapping"""
        if not data:
            return {"error": "No trajectory data available"}
            
        # Group by float_id for multiple trajectories
        trajectories = {}
        for item in data:
            float_id = item.get('float_id')
            if float_id not in trajectories:
                trajectories[float_id] = []
            
            if item.get('latitude') is not None and item.get('longitude') is not None:
                trajectories[float_id].append({
                    "latitude": item.get('latitude'),
                    "longitude": item.get('longitude'),
                    "cycle_number": item.get('cycle_number'),
                    "profile_date": item.get('profile_date')
                })
        
        return {
            "type": "trajectory_map",
            "trajectories": [
                {
                    "float_id": float_id,
                    "points": points,
                    "color": f"hsl({(float_id % 12) * 30}, 70%, 50%)"
                }
                for float_id, points in trajectories.items() if points
            ],
            "metadata": {
                "total_trajectories": len(trajectories),
                "total_points": sum(len(points) for points in trajectories.values())
            }
        }
    
    @staticmethod
    def format_timeseries_data(data: List[Dict], parameter: str = "temperature", float_id: Optional[int] = None) -> Dict[str, Any]:
        """Format time series data for frontend plotting"""
        if not data:
            return {"error": "No time series data available"}
            
        dates = []
        values = []
        for item in data:
            if item.get('profile_date') and item.get(parameter) is not None:
                try:
                    dates.append(item['profile_date'].isoformat() if hasattr(item['profile_date'], 'isoformat') else str(item['profile_date']))
                    values.append(item[parameter])
                except:
                    continue
        
        if not dates or not values:
            return {"error": f"No valid {parameter} time series data"}
            
        return {
            "type": "timeseries",
            "float_id": float_id,
            "parameter": parameter,
            "data": {
                "dates": dates,
                "values": values
            },
            "metadata": {
                "units": {
                    "parameter": "°C" if parameter == "temperature" else "PSU" if parameter == "salinity" else "dbar"
                },
                "date_range": [min(dates), max(dates)] if dates else [],
                "data_points": len(dates),
                "parameter_name": parameter.capitalize()
            }
        }
    
    @staticmethod
    def format_multi_parameter_data(data: List[Dict], float_id: int) -> Dict[str, Any]:
        """Format multi-parameter data for frontend comparison"""
        if not data:
            return {"error": "No multi-parameter data available"}
            
        depths = [item.get('pressure') for item in data if item.get('pressure') is not None]
        temperatures = [item.get('temperature') for item in data if item.get('temperature') is not None]
        salinities = [item.get('salinity') for item in data if item.get('salinity') is not None]
        
        return {
            "type": "multi_parameter",
            "float_id": float_id,
            "data": {
                "depths": depths,
                "temperatures": temperatures,
                "salinities": salinities
            },
            "metadata": {
                "units": {
                    "depth": "dbar",
                    "temperature": "°C",
                    "salinity": "PSU"
                },
                "data_points": {
                    "depth": len(depths),
                    "temperature": len(temperatures),
                    "salinity": len(salinities)
                }
            }
        }
    
    @staticmethod
    def format_region_data(region_data: Dict, region: str) -> Dict[str, Any]:
        """Format region data for frontend visualization"""
        if not region_data or 'floats' not in region_data:
            return {"error": "No region data available"}
            
        floats = region_data['floats']
        if not floats:
            return {"error": f"No floats found in {region} region"}
            
        institutions = {}
        for float_data in floats:
            institution = float_data.get('operating_institute', 'Unknown')
            institutions[institution] = institutions.get(institution, 0) + 1
            
        map_points = []
        for float_data in floats:
            if float_data.get('launch_latitude') and float_data.get('launch_longitude'):
                map_points.append({
                    "float_id": float_data.get('platform_number'),
                    "latitude": float_data.get('launch_latitude'),
                    "longitude": float_data.get('launch_longitude'),
                    "institution": float_data.get('operating_institute', 'Unknown'),
                    "project": float_data.get('project_name', 'Unknown')
                })
        
        return {
            "type": "regional_analysis",
            "region": region,
            "data": {
                "institution_counts": {
                    "institutions": list(institutions.keys()),
                    "counts": list(institutions.values())
                },
                "map_data": map_points,
                "float_metadata": floats
            },
            "metadata": {
                "total_floats": len(floats),
                "bounding_box": REGIONS.get(region, []),
                "institutions_count": len(institutions)
            }
        }
    
    @staticmethod
    def format_comparison_data(comparison_result: Dict) -> Dict[str, Any]:
        """Format comparison data for frontend visualization"""
        if "error" in comparison_result:
            return comparison_result
            
        return {
            "type": "float_comparison",
            "parameter": comparison_result.get("parameter", "temperature"),
            "data": comparison_result.get("comparison", {}),
            "metadata": {
                "float_ids": comparison_result.get("float_ids", []),
                "float_count": comparison_result.get("float_count", 0)
            }
        }

    @staticmethod
    def format_multiple_trajectories_data(trajectories_result: Dict) -> Dict[str, Any]:
        """Format multiple trajectories data for frontend mapping"""
        if "error" in trajectories_result:
            return trajectories_result
            
        return {
            "type": "multiple_trajectories_map",
            "trajectories": trajectories_result.get("trajectories", {}),
            "metadata": {
                "total_floats": trajectories_result.get("total_floats", 0),
                "trajectories_found": trajectories_result.get("trajectories_found", 0)
            }
        }

# ==================== CONVERSATION MEMORY ====================
class ConversationMemory:
    def __init__(self):
        self.sessions = defaultdict(dict)
        self.context_window = 10
    
    def add_exchange(self, session_id: str, query: str, response: dict, intent: str, entities: Dict[str, Any]):
        if session_id not in self.sessions:
            self.sessions[session_id] = {'history': [], 'context': {}, 'created_at': datetime.now()}
        
        exchange = {
            'timestamp': datetime.now(),
            'query': query,
            'response': response,
            'intent': intent,
            'entities': entities
        }
        
        self.sessions[session_id]['history'].append(exchange)
        self.sessions[session_id]['history'] = self.sessions[session_id]['history'][-self.context_window:]
        
        self.sessions[session_id]['context'].update(entities)
        
        if 'float_id' in entities:
            self.sessions[session_id]['context']['last_float_id'] = entities['float_id']
        if 'float_ids' in entities:
            self.sessions[session_id]['context']['last_float_ids'] = entities['float_ids']
        if 'parameter' in entities:
            self.sessions[session_id]['context']['last_parameter'] = entities['parameter']
        if 'region' in entities:
            self.sessions[session_id]['context']['last_region'] = entities['region']
    
    def get_context(self, session_id: str) -> dict:
        return self.sessions.get(session_id, {}).get('context', {})
    
    def get_history(self, session_id: str, last_n: int = 5) -> List[dict]:
        history = self.sessions.get(session_id, {}).get('history', [])
        return history[-last_n:]

# ==================== COMPREHENSIVE AI-FIRST MCP SERVER ====================
class OptimizedArgoMCPServer:
    def __init__(self):
        self.db_pool = None
        self.collection = None
        self.gemini_model = None
        self.supabase = None
        self.sql_generator = None
        self.data_formatter = DataFormatter()
        self.memory = ConversationMemory()
        
        self.execution_limits = {
            "max_tools_per_query": 6,
            "max_ai_calls_per_query": 2,
            "query_timeout": 30
        }
    
    # ==================== LAYER 1: AI DETECTION & TOOL SELECTION ====================
    async def layer1_ai_detection(self, query: str, context: dict) -> Dict[str, Any]:
        """LAYER 1: AI understands query and selects appropriate tool with STRICT validation"""
        try:
            tool_definitions = {
                "greeting": {
                    "params": [],
                    "description": "User is greeting (hello, hi, hey, good morning)",
                    "examples": ["hello", "hi there", "good morning", "hey"],
                    "returns_data": False
                },
                "farewell": {
                    "params": [],
                    "description": "User is saying goodbye",
                    "examples": ["bye", "goodbye", "see you", "thanks bye"],
                    "returns_data": False
                },
                "capabilities": {
                    "params": [],
                    "description": "User asking what the system can do",
                    "examples": ["what can you do", "help", "capabilities", "features"],
                    "returns_data": False
                },
                "list_all_floats": {
                    "params": ["limit", "offset"],
                    "description": "List/show all available floats",
                    "examples": ["show all floats", "list floats", "which floats do you have"],
                    "returns_data": True
                },
                "count_floats": {
                    "params": ["region"],
                    "description": "Count total number of floats, optionally in a region",
                    "examples": ["how many floats", "count floats", "total floats"],
                    "returns_data": True
                },
                "get_float_profile": {
                    "params": ["float_id", "cycle_number"],
                    "description": "Get complete metadata and profile for ONE specific float",
                    "examples": ["info about float 2902296", "details of float 2902296"],
                    "returns_data": True
                },
                "get_depth_profile": {
                    "params": ["float_id", "parameter", "cycle_number"],
                    "description": "Get depth profile of ONE parameter for ONE float",
                    "examples": ["temperature of float 2902296", "salinity profile of float 2902296"],
                    "returns_data": True,
                    "valid_parameters": ["temperature", "salinity", "pressure", "depth_m"]
                },
                "get_trajectory": {
                    "params": ["float_id"],
                    "description": "Get path/trajectory/route of ONE specific float",
                    "examples": ["path of float 2902296", "trajectory of float 2902296", "where did float 2902296 go"],
                    "returns_data": True
                },
                "get_multiple_trajectories": {
                    "params": ["float_ids"],
                    "description": "Get trajectory paths for MULTIPLE floats (bulk operation)",
                    "examples": ["locations of all floats", "trajectories of floats 2902296 and 2902297", "map paths for each float"],
                    "returns_data": True,
                    "important": "Use when query asks for locations of MULTIPLE floats"
                },
                "get_timeseries": {
                    "params": ["float_id", "parameter"],
                    "description": "Get time series data for ONE parameter of ONE float",
                    "examples": ["temperature over time for float 2902296"],
                    "returns_data": True,
                    "valid_parameters": ["temperature", "salinity", "pressure", "depth_m"]
                },
                "get_floats_in_region": {
                    "params": ["region"],
                    "description": "Get list of floats in a specific region (NO parameter data, just float IDs)",
                    "examples": ["floats in arabian sea", "show floats in indian ocean"],
                    "returns_data": True,
                    "valid_regions": ["arabian_sea", "indian_ocean", "bay_of_bengal", "equator", "south_atlantic", "north_pacific"],
                    "important": "This tool ONLY returns float IDs, NOT their parameter data"
                },
                "get_region_data": {
                    "params": ["region"],
                    "description": "Get metadata about floats in a region (NO parameter data)",
                    "examples": ["data about arabian sea region"],
                    "returns_data": True,
                    "important": "This tool ONLY returns metadata, NOT temperature/salinity data"
                },
                "search_floats_by_location": {
                    "params": ["latitude", "longitude", "radius"],
                    "description": "Find floats near specific coordinates",
                    "examples": ["floats near 15.0, 60.0", "find floats at latitude 15 longitude 60"],
                    "returns_data": True
                },
                "compare_floats": {
                    "params": ["float_ids", "parameter"],
                    "description": "Compare ONE parameter across multiple floats (needs 2+ float IDs)",
                    "examples": ["compare temperature of floats 2902296 and 2902297", "temperature of all floats", "compare all floats salinity"],
                    "returns_data": True,
                    "valid_parameters": ["temperature", "salinity", "pressure", "depth_m"],
                    "important": "Use for BULK comparison of multiple floats"
                }
            }
            
            prompt = f'''You are a STRICT tool selector for ARGO oceanographic data queries.

    YOUR ONLY JOB: Analyze the query and return EXACTLY ONE tool that can answer it, OR return null if impossible.

    📋 AVAILABLE TOOLS (with EXACT parameters):
    {json.dumps(tool_definitions, indent=2)}

    🚫 CRITICAL RULES - NEVER BREAK THESE:

    1. **Parameter Invention is FORBIDDEN**
    - ONLY use parameters listed in "params" for each tool
    - If a parameter doesn't exist in the tool definition, DO NOT include it

    2. **One Tool Rule**
    - You MUST select EXACTLY ONE tool OR return null
    - If query needs multiple steps (e.g., "temperature of floats in arabian sea"), return null
    - Queries requiring multiple tools → return null with "requires_multiple_tools": true

    3. **SINGLE vs MULTIPLE Float Detection**
    - SINGLE float: Mentions specific float ID or "one float" → use single tools (get_depth_profile, get_trajectory)
    - MULTIPLE floats: Mentions "floats", "all", "each", "multiple" → use bulk tools (compare_floats, get_multiple_trajectories)
    - REGIONAL queries: First get_floats_in_region, then choose appropriate single/bulk tools

    4. **Conversational Queries**
    - Greetings/farewells → use "greeting" or "farewell" tool (they exist!)
    - "What can you do?" → use "capabilities" tool
    - These should NEVER reach Layer 2 or Layer 3

    5. **Parameter Validation**
    - Only these parameters exist: temperature, salinity, pressure, depth_m
    - Only these regions exist: arabian_sea, indian_ocean, bay_of_bengal, equator, south_atlantic, north_pacific

    📊 CURRENT QUERY CONTEXT:
    Query: "{query}"
    Previous Context: {json.dumps(context, default=str)}

    🎯 YOUR RESPONSE FORMAT (JSON only, no explanations):

    For CONVERSATIONAL queries:
    {{
        "tool": "greeting",  // or "farewell" or "capabilities"
        "parameters": {{}},
        "confidence": 1.0,
        "reasoning": "User is greeting/asking about capabilities"
    }}

    For SIMPLE DATA queries (ONE tool can answer):
    {{
        "tool": "get_depth_profile",
        "parameters": {{"float_id": 2902296, "parameter": "temperature"}},
        "confidence": 0.98,
        "reasoning": "Single float, single parameter - direct tool match"
    }}

    For COMPLEX queries (multiple tools needed):
    {{
        "tool": null,
        "confidence": 0.0,
        "reasoning": "Query requires multiple steps: first get floats, then get their data",
        "requires_multiple_tools": true,
        "suggested_tools": ["get_floats_in_region", "get_depth_profile"]
    }}

    For UNCLEAR queries:
    {{
        "tool": null,
        "confidence": 0.0,
        "reasoning": "Query is ambiguous or cannot be answered with available tools"
    }}

    Now analyze the query and return ONLY valid JSON:
    '''
            
            response = await asyncio.to_thread(
                lambda: self.gemini_model.generate_content(prompt)
            )
            
            response_text = response.text.strip()
            response_text = response_text.replace('```json', '').replace('```', '').strip()
            
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                logger.error(f"Failed to parse AI response: {response_text}")
                result = {
                    "tool": None, 
                    "reasoning": "Failed to parse AI response",
                    "confidence": 0.0
                }
            
            validated_result = self._validate_layer1_response(result, tool_definitions)
            
            logger.info(f"LAYER 1 AI Detection: {validated_result}")
            return validated_result
            
        except Exception as e:
            logger.error(f"Layer 1 AI detection failed: {e}", exc_info=True)
            return {
                "tool": None, 
                "reasoning": f"AI detection failed: {str(e)}",
                "confidence": 0.0
            }

    def _validate_layer1_response(self, result: Dict, tool_definitions: Dict) -> Dict:
        """Validate that AI didn't hallucinate parameters"""
        tool = result.get('tool')
        
        if not tool or tool == 'null':
            return result
        
        if tool not in tool_definitions:
            logger.warning(f"AI selected non-existent tool: {tool}")
            return {
                "tool": None,
                "reasoning": f"Invalid tool selected: {tool}",
                "confidence": 0.0
            }
        
        expected_params = tool_definitions[tool]['params']
        provided_params = result.get('parameters', {})
        
        extra_params = set(provided_params.keys()) - set(expected_params)
        if extra_params:
            logger.warning(f"AI hallucinated parameters {extra_params} for tool {tool}")
            return {
                "tool": None,
                "reasoning": f"Tool {tool} doesn't accept parameters: {extra_params}",
                "confidence": 0.0,
                "validation_error": f"Invalid parameters provided"
            }
        
        if tool in ['get_depth_profile', 'get_timeseries', 'compare_floats']:
            param_value = provided_params.get('parameter')
            valid_params = tool_definitions[tool].get('valid_parameters', [])
            if param_value and param_value not in valid_params:
                logger.warning(f"Invalid parameter value: {param_value}")
                return {
                    "tool": None,
                    "reasoning": f"Invalid parameter '{param_value}'. Valid: {valid_params}",
                    "confidence": 0.0
                }
        
        if tool in ['get_floats_in_region', 'get_region_data']:
            region_value = provided_params.get('region')
            valid_regions = tool_definitions[tool].get('valid_regions', [])
            if region_value and region_value not in valid_regions:
                logger.warning(f"Invalid region: {region_value}")
                region_fixed = region_value.replace(' ', '_').lower()
                if region_fixed in valid_regions:
                    provided_params['region'] = region_fixed
                    result['parameters'] = provided_params
                    logger.info(f"Auto-corrected region: {region_value} → {region_fixed}")
                else:
                    return {
                        "tool": None,
                        "reasoning": f"Invalid region '{region_value}'. Valid: {valid_regions}",
                        "confidence": 0.0
                    }
        
        return result

    # ==================== LAYER 2: COMPREHENSIVE AI-POWERED ORCHESTRATION ====================
    async def layer2_complex_orchestration(self, query: str, context: dict) -> Dict[str, Any]:
        """LAYER 2: AI creates comprehensive plans for both single and multiple float queries"""
        try:
            prompt = f'''You are an AI orchestration planner for ARGO oceanographic data. Your task is to create COMPREHENSIVE multi-step plans.

    QUERY: "{query}"
    CONTEXT: {json.dumps(context, default=str)}

    🛠️ AVAILABLE TOOLS WITH EXACT SCHEMAS:

    1. get_floats_in_region(region)
       - Input: region (string from: equator, arabian_sea, indian_ocean, bay_of_bengal, south_atlantic, north_pacific)
       - Output: {{"region": "arabian_sea", "floats": [2902296, 2902297, ...], "float_count": 15}}

    2. get_depth_profile(float_id, parameter, cycle_number=null)
       - Input: float_id (integer), parameter (temperature/salinity/pressure/depth_m), cycle_number (optional integer)
       - Output: Depth profile data for ONE float

    3. compare_floats(float_ids, parameter)
       - Input: float_ids (array of integers), parameter (temperature/salinity/pressure/depth_m)
       - Output: Comparative statistics for MULTIPLE floats

    4. get_trajectory(float_id)
       - Input: float_id (integer)
       - Output: Trajectory path data for ONE float

    5. get_multiple_trajectories(float_ids)
       - Input: float_ids (array of integers)
       - Output: Trajectory paths for MULTIPLE floats (bulk operation)

    6. get_timeseries(float_id, parameter)
       - Input: float_id (integer), parameter (temperature/salinity/pressure/depth_m)
       - Output: Time series data for ONE float

    🔄 COMPREHENSIVE DATA FLOW RULES:

    1. **SINGLE FLOAT QUERIES** (mentions one specific float ID):
       - Use single tools: get_depth_profile, get_trajectory, get_timeseries
       - Example: "temperature of float 2903896" → get_depth_profile(2903896, "temperature")

    2. **MULTIPLE FLOAT QUERIES** (mentions "floats", "all", "each", "multiple"):
       - Use bulk tools: compare_floats, get_multiple_trajectories
       - Example: "temperature of all floats" → compare_floats(ALL_FLOAT_IDS, "temperature")
       - Example: "locations of floats" → get_multiple_trajectories(ALL_FLOAT_IDS)

    3. **REGIONAL QUERIES** (mentions regions):
       - First: get_floats_in_region(region) to get float IDs
       - Then: Choose appropriate single/bulk tools based on query intent

    4. **COMPREHENSIVE COVERAGE**:
       - If query asks for "location AND temp" → plan for BOTH trajectory AND temperature data
       - If query mentions "all" or "each" → use bulk tools for COMPLETE data
       - NEVER use single tools when user clearly wants data for multiple floats

    🎯 CRITICAL: Your plan MUST be COMPREHENSIVE. Return ONLY this JSON format:

    {{
        "plan": [
            {{
                "tool": "tool_name",
                "parameters": {{
                    "param1": "value1",
                    "param2": "EXTRACT:field_name"  // SPECIFY exact field to extract
                }},
                "purpose": "Clear purpose",
                "expected_output_structure": "Describe what this step returns"
            }}
        ],
        "expected_output": "What the final result will be",
        "data_flow_explanation": "How data moves between steps",
        "completeness_note": "Ensure ALL requested data types are covered"
    }}

    Now create a COMPREHENSIVE plan for the current query. Return ONLY valid JSON:
    '''
            
            response = await asyncio.to_thread(
                lambda: self.gemini_model.generate_content(prompt)
            )
            
            response_text = response.text.strip()
            response_text = response_text.replace('```json', '').replace('```', '').strip()
            
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                response_text = json_match.group()
            
            plan_data = json.loads(response_text)
            
            if "error" in plan_data:
                return {"error": plan_data["error"]}
            
            results = await self._execute_comprehensive_orchestration_plan(plan_data.get("plan", []))
            
            if not results or all("error" in str(result) for result in results.values()):
                return {"error": "All orchestration steps failed"}
            
            final_response = await self._synthesize_orchestration_results(
                query, results, plan_data.get("expected_output", "")
            )
            return final_response
            
        except json.JSONDecodeError as e:
            logger.error(f"Layer 2 JSON parse error: {e}")
            return {"error": "Failed to create execution plan"}
        except Exception as e:
            logger.error(f"Layer 2 complex orchestration failed: {e}")
            return {"error": f"Complex orchestration failed: {str(e)}"}
        
    async def _execute_comprehensive_orchestration_plan(self, plan: List[Dict]) -> Dict:
        """Execute comprehensive orchestration plan with smart parameter resolution"""
        results = {}
        previous_results = {}
        
        for step_index, step in enumerate(plan[:self.execution_limits["max_tools_per_query"]]):
            try:
                tool_name = step['tool']
                parameters = step.get('parameters', {})
                purpose = step.get('purpose', '')
                
                resolved_params = await self._comprehensive_resolve_parameters(step, previous_results, step_index)
                
                if "error" in resolved_params:
                    results[tool_name] = {"error": resolved_params["error"]}
                    continue
                
                logger.info(f"Executing orchestration step {step_index + 1}: {tool_name} for {purpose}")
                logger.info(f"Resolved parameters: {resolved_params}")
                
                if hasattr(self, tool_name):
                    result = await getattr(self, tool_name)(**resolved_params)
                    results[tool_name] = result
                    previous_results[tool_name] = result
                else:
                    results[tool_name] = {"error": f"Tool {tool_name} not found"}
                    
            except Exception as e:
                logger.error(f"Orchestration step failed for {tool_name}: {e}")
                results[tool_name] = {"error": str(e)}
        
        return results
    
    async def _comprehensive_resolve_parameters(self, step: Dict, previous_results: Dict, step_index: int) -> Dict:
        """Comprehensive parameter resolution for both single and multiple float queries"""
        tool_name = step['tool']
        parameters = step.get('parameters', {})
        resolved_params = {}
        
        if step_index == 0:
            return parameters
        
        previous_step_name = list(previous_results.keys())[-1]
        previous_result = previous_results[previous_step_name]
        
        prompt = f'''You are a comprehensive parameter resolver for ARGO data tools. Resolve parameters for step {step_index + 1}.

    CURRENT STEP:
    - Tool: {tool_name}
    - Parameters to resolve: {json.dumps(parameters, indent=2)}
    - Purpose: {step.get('purpose', '')}

    PREVIOUS STEP RESULT:
    {json.dumps(previous_result, default=str, indent=2)}

    COMPREHENSIVE RESOLUTION RULES:

    1. **BULK OPERATIONS** (for multiple floats):
       - compare_floats: Use ALL float IDs from "floats" array
       - get_multiple_trajectories: Use ALL float IDs from "floats" array
       - "EXTRACT:floats:ALL" → extract ALL platform_number values

    2. **SINGLE OPERATIONS** (for one float):
       - get_depth_profile: Use FIRST float ID unless specified
       - get_trajectory: Use FIRST float ID unless specified  
       - get_timeseries: Use FIRST float ID unless specified
       - "EXTRACT:floats[0]" → extract first platform_number

    3. **INTELLIGENT SELECTION**:
       - If previous step has MANY floats (>5) and tool is single-operation → use first float
       - If previous step has FEW floats (2-5) and query implies "all" → use ALL floats
       - If tool is specifically for bulk operations → ALWAYS use ALL floats

    Return ONLY JSON with resolved parameters:
    {{
        "resolved_parameters": {{
            "param1": "resolved_value1",
            "param2": "resolved_value2"
        }},
        "resolution_notes": "Brief explanation of choices"
    }}
    '''
        
        try:
            response = await asyncio.to_thread(
                lambda: self.gemini_model.generate_content(prompt)
            )
            
            response_text = response.text.strip()
            response_text = response_text.replace('```json', '').replace('```', '').strip()
            
            resolution_data = json.loads(response_text)
            resolved_params = resolution_data.get("resolved_parameters", {})
            
            logger.info(f"Comprehensive parameter resolution: {resolution_data.get('resolution_notes', '')}")
            
            return resolved_params
            
        except Exception as e:
            logger.error(f"Comprehensive parameter resolution failed: {e}")
            return {"error": f"Parameter resolution failed: {str(e)}"}
    
    async def _synthesize_orchestration_results(self, original_query: str, tool_results: Dict, expected_output: str) -> Dict:
        """Generate AI response from orchestration results"""
        prompt = f"""
        Original Query: "{original_query}"
        Expected Output: "{expected_output}"
        
        Tool Execution Results:
        {json.dumps(tool_results, default=str, indent=2)}
        
        Create a comprehensive, synthesized response that answers the original query using all the tool results.
        Provide key insights, patterns, and conclusions. Be specific about the data found.
        
        If there were any errors in the execution, acknowledge them but still provide insights from successful steps.
        
        IMPORTANT: Highlight whether we provided COMPLETE data (all floats) or SAMPLE data (some floats).
        """
        
        try:
            response = await asyncio.to_thread(
                lambda: self.gemini_model.generate_content(prompt)
            )
            return {
                "ai_synthesized_response": response.text,
                "tool_results": tool_results,
                "processing_source": "complex_orchestration"
            }
        except Exception as e:
            return {
                "error": "AI synthesis failed", 
                "tool_results": tool_results,
                "processing_source": "complex_orchestration"
            }

    # ==================== MAIN PROCESSING FLOW ====================
    async def process_query_optimized(self, query: str, session_id: str) -> Dict[str, Any]:
        """MAIN PROCESSING: 3-Layer AI-First Approach"""
        logger.info(f"PROCESSING QUERY: {query}, Session: {session_id}")
        
        context = self.memory.get_context(session_id)
        
        logger.info("LAYER 1: AI Detection & Tool Selection")
        layer1_result = await self.layer1_ai_detection(query, context)
        
        tool_name = layer1_result.get('tool')
        confidence = layer1_result.get('confidence', 0)
        
        if tool_name and confidence > 0.7:
            parameters = layer1_result.get('parameters', {})
            
            logger.info(f"LAYER 1 SUCCESS - Executing {tool_name} with {parameters}")
            
            if tool_name in ['greeting', 'farewell', 'capabilities']:
                result = self._handle_conversational_intent(tool_name)
                self.memory.add_exchange(session_id, query, result, tool_name, parameters)
                
                return {
                    "result": result,
                    "processing_source": "conversational",
                    "intent": tool_name,
                    "confidence": confidence,
                    "timestamp": datetime.now().isoformat()
                }
            
            result = await self.execute_tool(tool_name, parameters)
            self.memory.add_exchange(session_id, query, result, tool_name, parameters)
            
            return {
                "result": result,
                "processing_source": "single_tool",
                "intent": tool_name,
                "confidence": confidence,
                "timestamp": datetime.now().isoformat()
            }
        
        if layer1_result.get('requires_multiple_tools'):
            logger.info("LAYER 1 DETECTED MULTI-TOOL QUERY → LAYER 2: Complex Orchestration")
            layer2_result = await self.layer2_complex_orchestration(query, context)
            
            if layer2_result and not layer2_result.get("error"):
                logger.info("LAYER 2 SUCCESS - Complex orchestration completed")
                self.memory.add_exchange(session_id, query, layer2_result, "complex_orchestration", {})
                return {
                    "result": layer2_result,
                    "processing_source": "complex_orchestration", 
                    "intent": "complex_query",
                    "confidence": 0.7,
                    "timestamp": datetime.now().isoformat()
                }
        
        logger.info("LAYER 1 UNCERTAIN → LAYER 2: Complex Orchestration")
        
        if layer1_result.get('confidence', 0) == 0 and 'ambiguous' in layer1_result.get('reasoning', '').lower():
            return {
                "error": "Query is too vague or unclear for ARGO data analysis. Please ask specific questions about oceanographic data, float IDs, regions, or parameters.",
                "suggestions": [
                    "Try: 'temperature of float 2902296'",
                    "Try: 'floats in arabian sea'", 
                    "Try: 'list all floats'",
                    "Try: 'compare floats 2902296 and 2902297'",
                    "Try: 'locations of all floats in indian ocean'"
                ],
                "processing_source": "query_validation",
                "intent": "unclear_query",
                "confidence": 0.0,
                "timestamp": datetime.now().isoformat()
            }
        
        layer2_result = await self.layer2_complex_orchestration(query, context)
        
        if layer2_result and not layer2_result.get("error"):
            logger.info("LAYER 2 SUCCESS - Complex orchestration completed")
            self.memory.add_exchange(session_id, query, layer2_result, "complex_orchestration", {})
            return {
                "result": layer2_result,
                "processing_source": "complex_orchestration", 
                "intent": "complex_query",
                "confidence": 0.7,
                "timestamp": datetime.now().isoformat()
            }
        
        logger.info("LAYER 2 FAILED → LAYER 3: SQL Generation")
        layer3_result = await self.sql_generator.generate_sql_response(query, context)
        
        self.memory.add_exchange(session_id, query, layer3_result, "sql_generation", {})
        
        if layer3_result.get("success"):
            logger.info("LAYER 3 SUCCESS - SQL generation completed")
            return {
                "result": layer3_result,
                "processing_source": "sql_generation",
                "intent": "custom_query", 
                "confidence": 0.6,
                "timestamp": datetime.now().isoformat()
            }
        else:
            logger.info("ULTIMATE FALLBACK - Direct AI analysis")
            analysis = await self.analyze_with_llm(query)
            fallback_result = {"ai_analysis": analysis, "note": "Used ultimate fallback"}
            return {
                "result": fallback_result,
                "processing_source": "emergency_fallback",
                "intent": "llm_chat",
                "confidence": 0.1,
                "timestamp": datetime.now().isoformat()
            }
    
    # ==================== TOOL EXECUTION ====================
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single tool with parameters"""
        if not hasattr(self, tool_name):
            return {"error": f"Tool {tool_name} not found"}
        
        try:
            tool_func = getattr(self, tool_name)
            logger.info(f"Executing tool: {tool_name} with parameters: {parameters}")
            result = await tool_func(**parameters)
            logger.info(f"Tool {tool_name} execution completed")
            return result
        except Exception as e:
            logger.error(f"Tool execution failed for {tool_name}: {e}")
            return {"error": f"Tool execution failed: {str(e)}"}
    
    def _handle_conversational_intent(self, intent: str) -> Dict[str, Any]:
        """Handle conversational intents that don't need tools"""
        responses = {
            "greeting": {
                "message": "🌊 Hello! I'm your ARGO AI assistant specialized in oceanographic data. I can help you explore ARGO float data including temperature profiles, trajectories, regional analysis, and more!",
                "conversational": True,
                "suggestions": [
                    "Try: 'show me all floats'",
                    "Try: 'temperature of float 2902296'", 
                    "Try: 'floats in arabian sea'",
                    "Try: 'locations of all floats in indian ocean'",
                    "Try: 'compare temperature of floats 2902296 and 2902297'"
                ]
            },
            "farewell": {
                "message": "👋 Goodbye! Feel free to come back anytime to explore more ARGO ocean data. Have a great day!",
                "conversational": True
            },
            "capabilities": {
                "message": "🎯 I can help you with:\n\n" +
                        "📊 **Single Float Analysis:**\n" +
                        "• Temperature, salinity, pressure profiles for ONE float\n" +
                        "• Individual float trajectories and paths\n" +
                        "• Time series analysis for specific floats\n\n" +
                        "🌍 **Multiple Float Analysis:**\n" +
                        "• Compare parameters across MULTIPLE floats\n" +
                        "• Get trajectories for ALL floats in regions\n" +
                        "• Bulk analysis of float groups\n\n" +
                        "🗺️ **Regional Analysis:**\n" +
                        "• Find floats in ocean regions (Arabian Sea, Indian Ocean, etc.)\n" +
                        "• Regional temperature/salinity comparisons\n" +
                        "• Geographic distribution analysis\n\n" +
                        "🔍 **Search & Discovery:**\n" +
                        "• Find floats by location coordinates\n" +
                        "• Count and list available floats\n" +
                        "• Semantic search for float characteristics\n\n" +
                        "Just ask naturally! Examples:\n" +
                        "• 'Show temperature of float 2902296' (SINGLE)\n" +
                        "• 'Locations of all floats in indian ocean' (MULTIPLE)\n" +
                        "• 'Compare salinity of floats 2902296 and 2902297' (COMPARISON)\n" +
                        "• 'Temperature and location of floats in arabian sea' (COMPREHENSIVE)",
                "conversational": True,
                "available_tools": [
                    "Single float profiles & trajectories",
                    "Multiple float comparisons", 
                    "Bulk trajectory mapping",
                    "Regional float analysis",
                    "Location-based search",
                    "Time series analysis"
                ]
            }
        }
        
        return responses.get(intent, {
            "message": "I understand your query.",
            "conversational": True
        })

    # ==================== COMPREHENSIVE MCP TOOLS ====================
    
    async def query_measurements(self, float_id: Optional[int] = None, parameter: Optional[str] = None,
                               depth_range: Optional[Tuple[float, float]] = None,
                               cycle_range: Optional[Tuple[int, int]] = None, limit: int = 1000) -> Any:
        """Query ARGO measurements - returns raw data with visualization"""
        if not self.db_pool:
            return {"error": "Database not connected"}
        
        if not float_id and not depth_range and not parameter:
            return {"error": "At least one of float_id, depth_range, or parameter is required"}
        
        async with self.db_pool.acquire() as conn:
            sql = """
            SELECT m.float_id, m.cycle_number, m.n_level, m.pressure, m.depth_m, 
                   m.temperature, m.salinity, p.profile_date, p.latitude, p.longitude
            FROM measurements m
            LEFT JOIN profiles p ON m.float_id = p.float_id AND m.cycle_number = p.cycle_number
            WHERE 1=1
            """
            params = []
            
            if float_id:
                sql += f" AND m.float_id = ${len(params) + 1}"
                params.append(float_id)
            
            if depth_range:
                sql += f" AND m.pressure BETWEEN ${len(params) + 1} AND ${len(params) + 2}"
                params.extend(depth_range)
            
            if cycle_range:
                sql += f" AND m.cycle_number BETWEEN ${len(params) + 1} AND ${len(params) + 2}"
                params.extend(cycle_range)
            
            if parameter:
                if parameter not in ['temperature', 'salinity', 'pressure', 'depth_m']:
                    return {"error": f"Invalid parameter: {parameter}. Must be one of: temperature, salinity, pressure, depth_m"}
                sql += f" AND m.{parameter} IS NOT NULL"
            
            sql += f" ORDER BY m.float_id, m.cycle_number, m.n_level LIMIT ${len(params) + 1}"
            params.append(limit)
            
            try:
                rows = await conn.fetch(sql, *params)
                data = [dict(row) for row in rows]
                
                if not data:
                    return {"error": f"No data found for float {float_id} and parameter {parameter}"}
                
                result = {
                    "data": data,
                    "metadata": {
                        "float_id": float_id,
                        "parameter": parameter,
                        "total_points": len(data),
                        "depth_range": [min(r['pressure'] for r in data if r['pressure']), max(r['pressure'] for r in data if r['pressure'])] if data else None,
                        "value_range": [min(r[parameter] for r in data if r[parameter]), max(r[parameter] for r in data if r[parameter])] if parameter and data else None
                    },
                    "viz": {
                        "kind": "profile",
                        "spec": {
                            "x": parameter or "value",
                            "y": "pressure",
                            "x_label": parameter.replace('_', ' ').title() if parameter else "Value",
                            "y_label": "Pressure (dbar)",
                            "invert_y": True
                        }
                    }
                }
                
                logger.info(f"Retrieved {len(data)} measurements for float {float_id}")
                return result
                
            except Exception as e:
                logger.exception("Query error")
                err_msg = str(e) if str(e) else "Query failed; check server logs for details"
                return {"error": err_msg}

    async def get_float_profile(self, float_id: int, cycle_number: Optional[int] = None) -> Dict:
        """Get complete float profile - returns raw data"""
        if not self.db_pool:
            return {"error": "Database not connected"}
        
        async with self.db_pool.acquire() as conn:
            meta_sql = """
            SELECT platform_number as float_id, float_serial_number, launch_date, start_date, end_of_life,
                   launch_latitude, launch_longitude, firmware_version, pi_name, project_name,
                   deployment_platform, float_owner, operating_institute
            FROM float_metadata 
            WHERE platform_number = $1
            """
            meta_row = await conn.fetchrow(meta_sql, float_id)
            
            if not meta_row:
                return {"error": f"Float {float_id} not found"}
            
            data_sql = """
            SELECT m.cycle_number, m.n_level, m.pressure, m.depth_m, m.temperature, m.salinity,
                   p.profile_date, p.latitude, p.longitude, p.direction, p.max_depth, p.n_levels
            FROM measurements m
            LEFT JOIN profiles p ON m.float_id = p.float_id AND m.cycle_number = p.cycle_number
            WHERE m.float_id = $1
            """
            params = [float_id]
            
            if cycle_number:
                data_sql += " AND m.cycle_number = $2"
                params.append(cycle_number)
            
            data_sql += " ORDER BY m.cycle_number, m.n_level"
            
            try:
                data_rows = await conn.fetch(data_sql, *params)
                return {
                    "metadata": dict(meta_row),
                    "measurements": [dict(row) for row in data_rows]
                }
            except Exception as e:
                logger.exception("Profile query error")
                err_msg = str(e) if str(e) else "Profile query failed; see server logs for traceback"
                return {"error": err_msg}

    async def get_float_trajectory(self, float_id: int) -> List[Dict]:
        """Get float trajectory - returns raw data - FIXED"""
        if not self.db_pool:
            logger.error("Database not connected")
            return []  # ✅ Return empty list instead of error dict
        
        async with self.db_pool.acquire() as conn:
            sql = """
            SELECT float_id, cycle_number, profile_date, latitude, longitude, direction
            FROM profiles 
            WHERE float_id = $1 
            AND latitude IS NOT NULL 
            AND longitude IS NOT NULL 
            ORDER BY cycle_number
            """
            
            try:
                rows = await conn.fetch(sql, float_id)
                trajectory_data = [dict(row) for row in rows]
                
                if not trajectory_data:
                    logger.info(f"No trajectory data found in database for float {float_id}")
                else:
                    logger.info(f"Found {len(trajectory_data)} trajectory points for float {float_id}")
                    
                return trajectory_data  # ✅ Always returns List[Dict]
                
            except Exception as e:
                logger.exception("Trajectory query error")
                logger.error(f"Trajectory query failed for float {float_id}: {str(e)}")
                return []  # ✅ Return empty list instead of error dict

    async def get_multiple_trajectories(self, float_ids: List[int]) -> Dict:
        """Get trajectories for MULTIPLE floats - PROPERLY FIXED"""
        if not self.db_pool:
            return {"error": "Database not connected"}
        
        if not float_ids:
            return {"error": "No float IDs provided"}
        
        all_trajectories = {}
        successful_trajectories = 0
        
        for float_id in float_ids:
            try:
                trajectory_result = await self.get_trajectory(float_id)
                
                # FIX: Check if get_trajectory returned SUCCESS (has map_data) or ERROR
                if isinstance(trajectory_result, dict) and "map_data" in trajectory_result:
                    # ✅ SUCCESS - we have trajectory data
                    all_trajectories[float_id] = {
                        "trajectory_data": trajectory_result,
                        "data_points": trajectory_result.get("data_points", 0),
                        "status": "success"
                    }
                    successful_trajectories += 1
                    logger.info(f"✅ Successfully retrieved trajectory for float {float_id} with {trajectory_result.get('data_points', 0)} points")
                    
                elif isinstance(trajectory_result, dict) and "error" in trajectory_result:
                    # ❌ ERROR from get_trajectory
                    all_trajectories[float_id] = {
                        "error": trajectory_result["error"],
                        "status": "failed"
                    }
                    logger.warning(f"Trajectory failed for float {float_id}: {trajectory_result['error']}")
                    
                else:
                    # Unexpected response
                    all_trajectories[float_id] = {
                        "error": "Unexpected response from trajectory service",
                        "status": "error"
                    }
                    logger.error(f"Unexpected response for float {float_id}: {trajectory_result}")
                    
            except Exception as e:
                all_trajectories[float_id] = {
                    "error": f"Trajectory query failed: {str(e)}",
                    "status": "error"
                }
                logger.error(f"Exception getting trajectory for float {float_id}: {e}")
        
        # Build visualization data for successful trajectories
        viz_trajectories = []
        for float_id, trajectory_info in all_trajectories.items():
            if trajectory_info.get("status") == "success" and "trajectory_data" in trajectory_info:
                trajectory_data = trajectory_info["trajectory_data"]
                if "viz" in trajectory_data and "spec" in trajectory_data["viz"]:
                    viz_trajectories.append({
                        "float_id": float_id,
                        "points": trajectory_data["viz"]["spec"].get("points", [])
                    })
        
        return {
            "type": "multiple_trajectories",
            "float_ids": float_ids,
            "total_floats": len(float_ids),
            "successful_trajectories": successful_trajectories,
            "failed_trajectories": len(float_ids) - successful_trajectories,
            "trajectories_data": all_trajectories,
            "viz": {
                "kind": "multiple_trajectories_map",
                "spec": {
                    "trajectories": viz_trajectories
                }
            }
        }

    async def search_floats_semantic(self, query: str, n_results: int = 5) -> List[Dict]:
        """Semantic search for floats"""
        if not self.collection:
            return {"error": "Vector database not available"}
        
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            if results and results.get("documents"):
                docs = results["documents"][0]
                metadatas = results.get("metadatas", [[]])[0]
                ids = results.get("ids", [[]])[0]
                
                return [{
                    "id": ids[i] if i < len(ids) else None,
                    "document": docs[i] if i < len(docs) else None,
                    "metadata": metadatas[i] if i < len(metadatas) else {}
                } for i in range(len(docs))]
            
            return []
        except Exception as e:
            logger.error(f"Semantic search error: {e}")
            return {"error": str(e)}

    async def analyze_with_llm(self, query: str, context_data: Optional[List[Dict]] = None) -> str:
        """Direct AI analysis fallback"""
        if not self.gemini_model:
            return "LLM not available"
        
        context = ""
        if context_data:
            context = f"Data context: {json.dumps(context_data[:5], default=str)}\n"
        
        prompt = f"""You are an expert ARGO oceanographic data analyst. 
        
        User Query: {query}
        
        {context}
        
        Provide a detailed analysis based on the query and any provided data context.
        """
        
        try:
            response = await asyncio.to_thread(
                lambda: self.gemini_model.generate_content(prompt)
            )
            return response.text.strip()
        except Exception as e:
            return f"Analysis error: {str(e)}"

    async def export_data_ascii(self, float_id: int, format_type: str = "csv") -> str:
        """Export ARGO data in ASCII format"""
        if not self.db_pool:
            return "Database not connected"
        
        try:
            data = await self.query_measurements(float_id=float_id, limit=10000)
            if isinstance(data, dict) and data.get("error"):
                return data["error"]
            
            records = data if isinstance(data, list) else data.get("data", [])
            df = pd.DataFrame(records)
            
            if format_type == "csv":
                return df.to_csv(index=False)
            elif format_type == "tsv":
                return df.to_csv(index=False, sep="\t")
            else:
                return "Unsupported format. Use 'csv' or 'tsv'."
                
        except Exception as e:
            logger.error(f"Export error: {e}")
            return f"Export failed: {str(e)}"

    async def get_floats_in_region(self, region: str) -> Dict:
        """Get floats in specific region - returns raw data"""
        if not self.db_pool:
            return {"error": "Database not connected"}
        
        if region not in REGIONS:
            return {"error": f"Invalid region: {region}. Valid regions: {list(REGIONS.keys())}"}
        
        async with self.db_pool.acquire() as conn:
            lat_min, lat_max, lon_min, lon_max = REGIONS[region]
            
            sql = """
            SELECT DISTINCT float_id FROM profiles 
            WHERE latitude BETWEEN $1 AND $2 
            AND longitude BETWEEN $3 AND $4
            """
            try:
                rows = await conn.fetch(sql, lat_min, lat_max, lon_min, lon_max)
                float_ids = [r['float_id'] for r in rows]
                
                if not float_ids:
                    return {"region": region, "floats": [], "float_count": 0}
                
                placeholders = ','.join([f'${i+1}' for i in range(len(float_ids))])
                meta_sql = f"""
                SELECT platform_number, float_serial_number, launch_date, start_date, end_of_life,
                       launch_latitude, launch_longitude, firmware_version, pi_name, project_name,
                       deployment_platform, float_owner, operating_institute
                FROM float_metadata 
                WHERE platform_number IN ({placeholders})
                """
                meta_rows = await conn.fetch(meta_sql, *float_ids)
                
                return {
                    "region": region,
                    "bounding_box": REGIONS[region],
                    "float_count": len(float_ids),
                    "floats": [dict(row) for row in meta_rows]
                }
            except Exception as e:
                logger.error(f"Error fetching floats in region {region}: {e}")
                return {"error": str(e)}

    async def compare_floats(self, float_ids: List[int], parameter: str = "temperature") -> Dict:
        """Compare multiple floats - returns raw data"""
        if not self.db_pool:
            return {"error": "Database not connected"}
        
        if parameter not in ['temperature', 'salinity', 'pressure', 'depth_m']:
            return {"error": f"Invalid parameter: {parameter}"}
        
        if len(float_ids) < 2:
            return {"error": "At least two float IDs required"}
        
        async with self.db_pool.acquire() as conn:
            comparison_data = {}
            
            for float_id in float_ids:
                stats_sql = f"""
                SELECT 
                    AVG({parameter}) as avg_value,
                    MIN({parameter}) as min_value,
                    MAX({parameter}) as max_value,
                    COUNT({parameter}) as measurement_count
                FROM measurements m
                WHERE m.float_id = $1 AND m.{parameter} IS NOT NULL
                """
                stats_row = await conn.fetchrow(stats_sql, float_id)
                
                if stats_row:
                    meta_sql = """
                    SELECT platform_number, pi_name, operating_institute, project_name
                    FROM float_metadata 
                    WHERE platform_number = $1
                    """
                    meta_row = await conn.fetchrow(meta_sql, float_id)
                    
                    comparison_data[float_id] = {
                        "metadata": dict(meta_row) if meta_row else {"platform_number": float_id},
                        "statistics": dict(stats_row)
                    }
            
            return {
                "parameter": parameter,
                "comparison": comparison_data,
                "float_count": len(comparison_data),
                "float_ids": float_ids
            }

    async def get_temporal_analysis(self, float_id: int, parameter: str, 
                                  start_date: date, end_date: date) -> Dict:
        """Perform temporal analysis on float data - returns raw data"""
        if not self.db_pool:
            return {"error": "Database not connected"}
        
        if parameter not in ['temperature', 'salinity', 'pressure', 'depth_m']:
            return {"error": f"Invalid parameter: {parameter}"}
        
        async with self.db_pool.acquire() as conn:
            sql = f"""
            SELECT p.profile_date, m.{parameter}, p.latitude, p.longitude
            FROM measurements m
            LEFT JOIN profiles p ON m.float_id = p.float_id AND m.cycle_number = p.cycle_number
            WHERE m.float_id = $1 
            AND p.profile_date BETWEEN $2 AND $3
            AND m.{parameter} IS NOT NULL
            ORDER BY p.profile_date
            """
            try:
                rows = await conn.fetch(sql, float_id, start_date, end_date + timedelta(days=1))
                data = [dict(row) for row in rows]
                
                if not data:
                    return {"error": f"No {parameter} data found for float {float_id} between {start_date} and {end_date}"}
                
                values = [item[parameter] for item in data if item.get(parameter) is not None]
                dates = [item['profile_date'] for item in data if item.get('profile_date') is not None]
                
                if not values:
                    return {"error": f"No valid {parameter} values found"}
                
                meta_sql = """
                SELECT platform_number, pi_name, operating_institute, project_name
                FROM float_metadata 
                WHERE platform_number = $1
                """
                meta_row = await conn.fetchrow(meta_sql, float_id)
                
                return {
                    "metadata": dict(meta_row) if meta_row else {"platform_number": float_id},
                    "parameter": parameter,
                    "start_date": start_date,
                    "end_date": end_date,
                    "statistics": {
                        "count": len(values),
                        "mean": sum(values) / len(values),
                        "min": min(values),
                        "max": max(values),
                        "date_range": [min(dates), max(dates)] if dates else None
                    },
                    "data": data
                }
            except Exception as e:
                logger.error(f"Temporal analysis error: {e}")
                return {"error": str(e)}

    async def get_depth_profile(self, float_id: int, cycle_number: Optional[int] = None, 
                          parameter: str = "temperature") -> Dict:
        """Get depth profile data for frontend plotting"""
        if parameter not in ['temperature', 'salinity', 'pressure', 'depth_m']:
            return {"error": f"Invalid parameter: {parameter}"}

        if cycle_number:
            query_result = await self.query_measurements(float_id=float_id, cycle_range=(cycle_number, cycle_number), limit=1000)
        else:
            query_result = await self.query_measurements(float_id=float_id, limit=1000)

        if isinstance(query_result, dict) and "error" in query_result:
            return query_result
        
        measurements_data = query_result.get("data", [])

        if not measurements_data:
            return {"error": f"No measurement data found for float {float_id}"}

        formatted_data = self.data_formatter.format_depth_profile_data(measurements_data, parameter, float_id)

        return {
            "float_id": float_id,
            "cycle_number": cycle_number,
            "parameter": parameter,
            "data_points": len(measurements_data),
            "plot_data": formatted_data
        }

    async def get_trajectory(self, float_id: int) -> Dict:
        """Get trajectory data for frontend mapping - FIXED"""
        try:
            logger.info(f"Getting trajectory for float {float_id}")
            data = await self.get_float_trajectory(float_id)
            
            # Now data is ALWAYS a list (empty or with points)
            if not data:  # ✅ Simple check - empty list means no data
                logger.info(f"No trajectory data available for float {float_id}")
                return {"error": f"No trajectory data found for float {float_id}"}
            
            # SUCCESS: We have valid trajectory data
            logger.info(f"✅ Raw trajectory data: {len(data)} points for float {float_id}")
            formatted_data = self.data_formatter.format_trajectory_data(data)
            
            if isinstance(formatted_data, dict) and formatted_data.get("error"):
                logger.error(f"Error formatting trajectory: {formatted_data.get('error')}")
                return formatted_data
            
            result = {
                "float_id": float_id,
                "data_points": len(data),
                "map_data": formatted_data,
                "viz": {
                    "kind": "map",
                    "spec": {
                        "points": [
                            {
                                "lat": point.get("latitude"),
                                "lon": point.get("longitude"),
                                "float_id": float_id
                            }
                            for point in data if point.get("latitude") is not None and point.get("longitude") is not None
                        ]
                    }
                }
            }
            logger.info(f"✅ SUCCESS: Returning {len(data)} trajectory points for float {float_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error in get_trajectory: {str(e)}", exc_info=True)
            return {"error": f"Failed to get trajectory: {str(e)}"}

    async def get_timeseries(self, float_id: int, parameter: str = "temperature") -> Dict:
        """Get time series data for frontend plotting"""
        if parameter not in ['temperature', 'salinity', 'pressure', 'depth_m']:
            return {"error": f"Invalid parameter: {parameter}"}
        
        end_date = date.today()
        start_date = end_date - timedelta(days=365)
        
        data = await self.get_temporal_analysis(float_id, parameter, start_date, end_date)
        if isinstance(data, dict) and data.get("error"):
            return data
        
        ts_data = data.get("data", [])
        formatted_data = self.data_formatter.format_timeseries_data(ts_data, parameter, float_id)
        
        return {
            "float_id": float_id,
            "parameter": parameter,
            "data_points": len(ts_data),
            "timeseries_data": formatted_data,
            "date_range": [start_date, end_date]
        }

    async def get_region_data(self, region: str) -> Dict:
        """Get region data for frontend visualization"""
        region_data = await self.get_floats_in_region(region)
        if isinstance(region_data, dict) and region_data.get("error"):
            return region_data
        
        formatted_data = self.data_formatter.format_region_data(region_data, region)
        
        return {
            "region": region,
            "float_count": region_data.get("float_count", 0),
            "region_data": formatted_data
        }

    async def list_all_floats(self, limit: int = 10, offset: int = 0) -> Dict:
        """List all available floats with visualization data"""
        if not self.db_pool:
            return {"error": "Database not connected"}
        
        async with self.db_pool.acquire() as conn:
            try:
                total_count = await conn.fetchval("SELECT COUNT(*) FROM float_metadata")
                
                sql = """
                SELECT platform_number, float_serial_number, launch_date, 
                       launch_latitude, launch_longitude, 
                       operating_institute, project_name,
                       (SELECT profile_date 
                        FROM profiles p 
                        WHERE p.float_id = float_metadata.platform_number 
                        ORDER BY profile_date DESC LIMIT 1) as last_profile_date
                FROM float_metadata 
                ORDER BY 
                    CASE WHEN (
                        SELECT profile_date 
                        FROM profiles p 
                        WHERE p.float_id = float_metadata.platform_number 
                        ORDER BY profile_date DESC LIMIT 1
                    ) IS NOT NULL THEN 0 ELSE 1 END,
                    last_profile_date DESC NULLS LAST,
                    platform_number
                LIMIT $1 OFFSET $2
                """
                
                rows = await conn.fetch(sql, limit, offset)
                floats = [dict(r) for r in rows]
                
                result = {
                    "floats": floats,
                    "total_count": total_count,
                    "returned_count": len(floats),
                    "has_more": (offset + limit) < total_count,
                    "viz": {
                        "kind": "float_list",
                        "spec": {
                            "points": [
                                {
                                    "float_id": float_data["platform_number"],
                                    "lat": float_data["launch_latitude"],
                                    "lon": float_data["launch_longitude"],
                                    "institution": float_data["operating_institute"],
                                    "last_profile": float_data["last_profile_date"].isoformat() if float_data.get("last_profile_date") else None
                                }
                                for float_data in floats
                                if float_data.get("launch_latitude") is not None 
                                and float_data.get("launch_longitude") is not None
                            ]
                        }
                    }
                }
                
                logger.info(f"Retrieved {len(floats)} floats out of {total_count} total")
                return result
                
            except Exception as e:
                logger.error(f"Error listing floats: {e}", exc_info=True)
                return {"error": f"Failed to list floats: {str(e)}"}

    async def count_floats(self, region: Optional[str] = None) -> Dict:
        """Count total floats and breakdown by institution. Can be filtered by region."""
        if not self.db_pool:
            return {"error": "Database not connected"}
            
        async with self.db_pool.acquire() as conn:
            try:
                float_ids_in_region = None
                if region:
                    if region not in REGIONS:
                        return {"error": f"Invalid region: {region}. Valid regions: {list(REGIONS.keys())}"}
                    
                    lat_min, lat_max, lon_min, lon_max = REGIONS[region]
                    
                    region_float_ids_sql = """
                        SELECT DISTINCT float_id FROM profiles 
                        WHERE latitude BETWEEN $1 AND $2 AND longitude BETWEEN $3 AND $4
                    """
                    rows = await conn.fetch(region_float_ids_sql, lat_min, lat_max, lon_min, lon_max)
                    float_ids_in_region = [r['float_id'] for r in rows]

                    if not float_ids_in_region:
                        return {
                            "total_floats": 0, "active_floats": 0, "by_institution": [], "by_project": [], "region": region,
                            "viz": {"kind": "summary", "spec": {"total": 0, "active": 0, "institutions": 0, "projects": 0}}
                        }

                total_count_query = "SELECT COUNT(DISTINCT platform_number) FROM float_metadata"
                inst_counts_query = "SELECT operating_institute, COUNT(*) as count FROM float_metadata"
                proj_counts_query = "SELECT project_name, COUNT(*) as count FROM float_metadata"
                active_count_query = "SELECT COUNT(DISTINCT float_id) FROM profiles WHERE profile_date >= NOW() - INTERVAL '30 days'"

                meta_params = []
                if float_ids_in_region is not None:
                    placeholders = ','.join(f'${i+1}' for i in range(len(float_ids_in_region)))
                    meta_where_clause = f" WHERE platform_number IN ({placeholders})"
                    total_count_query += meta_where_clause
                    inst_counts_query += meta_where_clause
                    proj_counts_query += meta_where_clause
                    meta_params = float_ids_in_region
                
                inst_counts_query += " GROUP BY operating_institute ORDER BY count DESC"
                proj_counts_query += " GROUP BY project_name ORDER BY count DESC"

                total_count = await conn.fetchval(total_count_query, *meta_params)
                inst_counts = await conn.fetch(inst_counts_query, *meta_params)
                proj_counts = await conn.fetch(proj_counts_query, *meta_params)

                active_params = []
                if float_ids_in_region is not None:
                    placeholders = ','.join(f'${i+1}' for i in range(len(float_ids_in_region)))
                    active_count_query += f" AND float_id IN ({placeholders})"
                    active_params = float_ids_in_region
                
                active_count = await conn.fetchval(active_count_query, *active_params)

                result = {
                    "total_floats": total_count or 0,
                    "active_floats": active_count or 0,
                    "by_institution": [
                        {"institution": row['operating_institute'] or 'Unknown', "count": row['count']}
                        for row in inst_counts
                    ],
                    "by_project": [
                        {"project": row['project_name'] or 'Unknown', "count": row['count']}
                        for row in proj_counts
                    ],
                    "viz": {
                        "kind": "summary",
                        "spec": {
                            "total": total_count or 0,
                            "active": active_count or 0,
                            "institutions": len(inst_counts),
                            "projects": len(proj_counts)
                        }
                    }
                }
                if region:
                    result["region"] = region

                return result
                
            except Exception as e:
                logger.error(f"Error counting floats: {str(e)}", exc_info=True)
                return {"error": f"Failed to count floats: {str(e)}"}

    async def search_floats_by_location(self, latitude: float, longitude: float, radius: float = 5.0) -> Dict:
        """Search for floats near a specific latitude/longitude within a radius (in degrees)"""
        if not self.db_pool:
            return {"error": "Database not connected"}
            
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                    SELECT DISTINCT f.*, 
                           2 * 6371 * asin(sqrt(
                               sin(radians($1 - p.latitude)/2)^2 + 
                               cos(radians(p.latitude)) * cos(radians($1)) * 
                               sin(radians($2 - p.longitude)/2)^2
                           )) as distance_km
                    FROM float_metadata f
                    JOIN profiles p ON f.platform_number = p.float_id
                    WHERE ABS(p.latitude - $1) <= $3 
                    AND ABS(p.longitude - $2) <= $3
                    ORDER BY distance_km ASC
                    LIMIT 10;
                """
                
                rows = await conn.fetch(query, latitude, longitude, radius)
                floats = []
                
                for row in rows:
                    float_data = dict(row)
                    distance = float_data.pop('distance_km', None)
                    floats.append({
                        "float_data": float_data,
                        "distance_km": distance
                    })
                
                return {
                    "success": True,
                    "type": "location_search",
                    "center": {"latitude": latitude, "longitude": longitude},
                    "radius_degrees": radius,
                    "floats_found": len(floats),
                    "floats": floats
                }
                
        except Exception as e:
            logger.error(f"Location search failed: {str(e)}", exc_info=True)
            return {"error": f"Failed to search floats by location: {str(e)}"}

    # ==================== UTILITY METHODS ====================
    def get_tool_list(self) -> List[str]:
        """Get list of available MCP tools"""
        return [
            "query_measurements", "get_float_profile", "get_float_trajectory",
            "search_floats_semantic", "analyze_with_llm", "export_data_ascii",
            "get_floats_in_region", "compare_floats", "get_temporal_analysis",
            "get_depth_profile", "get_trajectory", "get_timeseries", "get_multiple_trajectories",
            "get_region_data", "list_all_floats", "count_floats",
            "search_floats_by_location"
        ]
    
    async def set_database_pool(self, pool):
        self.db_pool = pool
    
    async def set_collection(self, collection):
        self.collection = collection
    
    async def set_gemini_model(self, model):
        self.gemini_model = model
    
    async def set_supabase(self, supabase):
        self.supabase = supabase
        self.sql_generator = SQLGenerationSystem(self.gemini_model, supabase, self.db_pool)

# ==================== FASTAPI APPLICATION ====================

# Global instances
mcp_server = OptimizedArgoMCPServer()

# Database schema creation
async def create_tables(conn):
    """Create database tables aligned with CSV file structures"""
    
    await conn.execute("""
    CREATE TABLE IF NOT EXISTS float_metadata (
        platform_number INTEGER PRIMARY KEY,
        float_serial_number INTEGER,
        launch_date TIMESTAMP,
        start_date TIMESTAMP,
        end_of_life TIMESTAMP,
        launch_latitude DOUBLE PRECISION,
        launch_longitude DOUBLE PRECISION,
        firmware_version TEXT,
        pi_name TEXT,
        project_name TEXT,
        deployment_platform TEXT,
        float_owner TEXT,
        operating_institute TEXT,
        created_at TIMESTAMP DEFAULT NOW()
    )
    """)
    
    await conn.execute("""
    CREATE TABLE IF NOT EXISTS profiles (
        id SERIAL PRIMARY KEY,
        float_id INTEGER NOT NULL,
        cycle_number INTEGER NOT NULL,
        profile_date TIMESTAMP,
        latitude DOUBLE PRECISION,
        longitude DOUBLE PRECISION,
        direction TEXT,
        max_depth DOUBLE PRECISION,
        n_levels INTEGER,
        created_at TIMESTAMP DEFAULT NOW(),
        UNIQUE (float_id, cycle_number)
    )
    """)
    
    await conn.execute("""
    CREATE TABLE IF NOT EXISTS measurements (
        id SERIAL PRIMARY KEY,
        float_id INTEGER NOT NULL,
        cycle_number INTEGER NOT NULL,
        n_level INTEGER NOT NULL,
        pressure DOUBLE PRECISION,
        depth_m DOUBLE PRECISION,
        temperature DOUBLE PRECISION,
        salinity DOUBLE PRECISION,
        created_at TIMESTAMP DEFAULT NOW(),
        UNIQUE (float_id, cycle_number, n_level)
    )
    """)
    
    await conn.execute("CREATE INDEX IF NOT EXISTS measurements_float_id_idx ON measurements(float_id);")
    await conn.execute("CREATE INDEX IF NOT EXISTS measurements_cycle_idx ON measurements(cycle_number);")
    await conn.execute("CREATE INDEX IF NOT EXISTS profiles_float_id_idx ON profiles(float_id);")
    await conn.execute("CREATE INDEX IF NOT EXISTS profiles_cycle_idx ON profiles(cycle_number);")
    
    logger.info("Database tables and indexes checked/created successfully.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting ARGO AI Optimized System - AI-First 3-Layer Approach...")
    
    try:
        app.state.pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=5,
            max_size=20,
            statement_cache_size=0,
            command_timeout=30
        )
        await mcp_server.set_database_pool(app.state.pool)
        logger.info("Database pool created successfully")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        app.state.pool = None

    genai.configure(api_key=GEMINI_API_KEY)
    app.state.gemini_model = genai.GenerativeModel("gemini-2.5-flash")
    await mcp_server.set_gemini_model(app.state.gemini_model)

    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    app.state.chroma = chromadb.PersistentClient(path="./chroma_db")
    app.state.collection = app.state.chroma.get_or_create_collection(
        name="argo_metadata", embedding_function=ef
    )
    await mcp_server.set_collection(app.state.collection)

    app.state.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    await mcp_server.set_supabase(app.state.supabase)

    if app.state.pool:
        async with app.state.pool.acquire() as conn:
            await create_tables(conn)

    yield
    
    logger.info("Shutting down ARGO AI Optimized System...")
    if hasattr(app.state, 'pool') and app.state.pool:
        await app.state.pool.close()
        logger.info("Database pool closed successfully")

app = FastAPI(
    title="ARGO AI Optimized System - AI-First 3-Layer Approach",
    description="Complete ARGO oceanographic data system with AI-first processing",
    version="3.0.0",
    lifespan=lifespan
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ==================== API ENDPOINTS ====================
@app.get("/")
async def root():
    return {
        "message": "🌊 ARGO AI Optimized System - AI-First 3-Layer v3.0",
        "status": "ready",
        "architecture": [
            "✅ Layer 1: AI Detection & Tool Selection",
            "✅ Layer 2: Complex Orchestration", 
            "✅ Layer 3: SQL Generation Fallback",
            "✅ AI-First Approach - No Rule-Based Flaws",
            "✅ Comprehensive Single & Multiple Float Support"
        ],
        "available_tools": mcp_server.get_tool_list(),
        "regions": list(REGIONS.keys())
    }

@app.get("/health")
async def health_check():
    if not app.state.pool:
        return {"status": "unhealthy", "database": "disconnected"}
    try:
        async with app.state.pool.acquire() as conn:
            tables = await conn.fetch("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('measurements', 'float_metadata', 'profiles')
            """)
            table_count = len(tables)
            await conn.fetchval("SELECT 1")
        return {
            "status": "healthy", 
            "database": "connected",
            "tables_available": table_count,
            "vector_db": "connected" if app.state.collection else "disconnected",
            "llm": "connected" if app.state.gemini_model else "disconnected",
            "supabase": "connected" if app.state.supabase else "disconnected",
            "tools_available": len(mcp_server.get_tool_list()),
            "memory_sessions": len(mcp_server.memory.sessions)
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}

@app.post("/query")
async def process_query(payload: Dict[str, Any]):
    """Main query endpoint using optimized AI-first approach"""
    query = payload.get("query", "").strip()
    session_id = payload.get("session_id", str(uuid.uuid4()))
    
    if not query:
        raise HTTPException(status_code=400, detail="Query text required")
    
    logger.info(f"Processing query: {query} (session: {session_id})")
    
    try:
        result = await mcp_server.process_query_optimized(query, session_id)

        inner = result.get("result") if isinstance(result, dict) else None
        if isinstance(inner, dict) and "error" in inner:
            detail = inner.get("error") or "Query failed; see server logs for details"
            raise HTTPException(status_code=404, detail=detail)

        if isinstance(inner, dict):
            merged = {**result}
            merged.update(inner)
            merged.pop("result", None)
            merged["session_id"] = session_id
            merged["query"] = query
            return merged

        return {
            **result,
            "session_id": session_id,
            "query": query
        }
    except Exception as e:
        logger.error(f"Query processing failed: {e}")
        analysis = await mcp_server.analyze_with_llm(query)
        return {
            "result": {"ai_analysis": analysis},
            "processing_source": "system_error_fallback",
            "intent": "error",
            "confidence": 0.0,
            "session_id": session_id,
            "error": "System error occurred"
        }

@app.get("/session/{session_id}/history")
async def get_session_history(session_id: str):
    """Get conversation history for a session"""
    return {
        "session_id": session_id,
        "history": mcp_server.memory.get_history(session_id),
        "context": mcp_server.memory.get_context(session_id)
    }

@app.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """Clear a specific session"""
    if session_id in mcp_server.memory.sessions:
        del mcp_server.memory.sessions[session_id]
        return {"status": "success", "message": f"Session {session_id} cleared"}
    else:
        return {"status": "error", "message": f"Session {session_id} not found"}

# Additional endpoints for direct access
@app.get("/floats")
async def list_floats(limit: int = 100, offset: int = 0):
    """List all available floats"""
    result = await mcp_server.list_all_floats(limit, offset)
    if isinstance(result, dict) and "error" in result:
        detail = result.get("error") or "Failed to list floats; check server logs for details"
        raise HTTPException(status_code=404, detail=detail)
    return result

@app.get("/float/{float_id}")
async def get_float_details(float_id: int):
    """Get detailed information about a specific float"""
    result = await mcp_server.get_float_profile(float_id)
    if isinstance(result, dict) and "error" in result:
        detail = result.get("error") or f"Float {float_id} could not be retrieved; check server logs"
        raise HTTPException(status_code=404, detail=detail)
    return result

@app.get("/data/depth_profile/{float_id}")
async def get_depth_profile_data(float_id: int, parameter: str = "temperature"):
    """Get depth profile data for frontend plotting"""
    result = await mcp_server.get_depth_profile(float_id, None, parameter)
    if isinstance(result, dict) and "error" in result:
        detail = result.get("error") or f"Depth profile for float {float_id} not available; see server logs"
        raise HTTPException(status_code=404, detail=detail)
    return result

@app.get("/data/trajectory/{float_id}")
async def get_trajectory_data(float_id: int):
    """Get trajectory data for frontend mapping"""
    result = await mcp_server.get_trajectory(float_id)
    if isinstance(result, dict) and "error" in result:
        detail = result.get("error") or f"Trajectory for float {float_id} not available; see server logs"
        raise HTTPException(status_code=404, detail=detail)
    return result

@app.get("/data/timeseries/{float_id}")
async def get_timeseries_data(float_id: int, parameter: str = "temperature"):
    """Get time series data for frontend plotting"""
    result = await mcp_server.get_timeseries(float_id, parameter)
    if isinstance(result, dict) and "error" in result:
        detail = result.get("error") or f"Timeseries for float {float_id} not available; see server logs"
        raise HTTPException(status_code=404, detail=detail)
    return result

@app.get("/data/region/{region_name}")
async def get_region_data(region_name: str):
    """Get data for a specific region"""
    result = await mcp_server.get_region_data(region_name)
    if isinstance(result, dict) and "error" in result:
        detail = result.get("error") or f"Region data for {region_name} not available; see server logs"
        raise HTTPException(status_code=404, detail=detail)
    return result

@app.post("/compare")
async def compare_floats(payload: Dict[str, Any]):
    """Compare multiple floats"""
    float_ids = payload.get("float_ids", [])
    parameter = payload.get("parameter", "temperature")
    
    if len(float_ids) < 2:
        raise HTTPException(status_code=400, detail="At least two float IDs required for comparison")
    
    result = await mcp_server.compare_floats(float_ids, parameter)
    if isinstance(result, dict) and "error" in result:
        detail = result.get("error") or "Comparison failed; see server logs for details"
        raise HTTPException(status_code=404, detail=detail)
    return result

@app.post("/trajectories/multiple")
async def get_multiple_trajectories(payload: Dict[str, Any]):
    """Get trajectories for multiple floats"""
    float_ids = payload.get("float_ids", [])
    
    if len(float_ids) < 1:
        raise HTTPException(status_code=400, detail="At least one float ID required")
    
    result = await mcp_server.get_multiple_trajectories(float_ids)
    if isinstance(result, dict) and "error" in result:
        detail = result.get("error") or "Multiple trajectories failed; see server logs for details"
        raise HTTPException(status_code=404, detail=detail)
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)