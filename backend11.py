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

# main.py - CORRECTED TO MATCH YOUR CSV STRUCTURES
import os
import re
import asyncio
import logging
import json
import uuid
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List, AsyncGenerator, Tuple
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
GEMINI_API_KEY = "AIzaSyAOyp8Imde-v1_0-Kuu16pBDRtPhOFRy0U"
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
            FLOAT_ID, CYCLE_NUMBER, N_LEVEL, PRESSURE, DEPTH_M, TEMP, PSAL
        )

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
            "SQL": "SELECT TEMP, PSAL FROM measurements WHERE FLOAT_ID = 2901456 AND ABS(PRESSURE - 500) <= 10 LIMIT 100;",
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

# ==================== DATA FORMATTER (REPLACES VISUALIZATION GENERATOR) ====================
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
                    "color": f"hsl({(float_id % 12) * 30}, 70%, 50%)"  # Generate consistent colors
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
            
        # Count floats by institution
        institutions = {}
        for float_data in floats:
            institution = float_data.get('operating_institute', 'Unknown')
            institutions[institution] = institutions.get(institution, 0) + 1
            
        # Prepare map data
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
        
        # Update context with entities
        self.sessions[session_id]['context'].update(entities)
        
        # Store references for resolution
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

# ==================== HYBRID INTENT PROCESSOR ====================
class HybridIntentProcessor:
    def __init__(self, mcp_server):
        self.mcp_server = mcp_server
    
    # ========== LAYER 1: RULES-BASED PROCESSING ==========
    def detect_intent_rules(self, q: str) -> str:
        """Rule-based intent detection - LAYER 1"""
        q = q.lower()
        rules = [
            (["hello", "hi", "hey"], "greeting"),
            (["bye", "goodbye"], "farewell"),
            (["how many floats", "count floats", "number of floats", "total floats"], "count_metadata"),
            (["path", "trajectory", "track", "route"], "profile_path"),
            (["profile", "temperature", "salinity", "pressure", "depth"], "data_query"),
            (["timeseries", "time series", "temporal"], "profile_timeseries"),
            (["metadata", "info", "details"], "metadata_details"),
            (["near", "close to", "around", "latitude", "longitude", "find floats"], "location_search"),
            (["similar", "like", "related", "closest"], "semantic_search"),
            (["compare", "comparison", "vs", "versus", "difference"], "profile_comparison"),
            (["region", "area", "basin"], "region_data"),
            (["download", "export", "get data"], "data_export"),
            (["map", "location", "where", "positions"], "map_visualization"),
            (["show floats", "list floats", "which floats", "available floats", "all floats", "show me some floats", "show me floats"], "list_floats"),
            (["cycle", "mission", "dive"], "cycle_data"),
        ]
        
        for keywords, intent in rules:
            if any(w in q for w in keywords):
                return intent
        return "unknown"
    
    def extract_entities_rules(self, text: str) -> Dict[str, Any]:
        """Enhanced entity extraction with multi-parameter and location support"""
        entities = {}
        text_lower = text.lower()
        
        # Extract float IDs
        float_matches = re.findall(r"\b(\d{5,8})\b", text)
        if float_matches:
            # For comparison queries, use float_ids
            if any(kw in text_lower for kw in ["compare", "comparison", "vs", "versus"]):
                entities['float_ids'] = [int(float_id) for float_id in float_matches]
            # For all other queries with a single float or multiple floats, just use float_id
            else:
                entities['float_id'] = int(float_matches[0])
                
        # Extract latitude/longitude
        lat_matches = re.findall(r"latitude\s*([-+]?\d*\.?\d+)", text_lower)
        lon_matches = re.findall(r"longitude\s*([-+]?\d*\.?\d+)", text_lower)
        if lat_matches and lon_matches:
            entities['latitude'] = float(lat_matches[0])
            entities['longitude'] = float(lon_matches[0])
        
        # Extract MULTIPLE parameters
        text_lower = text.lower()
        parameters = []
        param_mapping = {
            "temperature": ["temperature", "temp", "heat"],
            "salinity": ["salinity", "salt", "saltiness"], 
            "pressure": ["pressure", "depth", "deep"]
        }
        
        for param, keywords in param_mapping.items():
            if any(keyword in text_lower for keyword in keywords):
                parameters.append(param)
        
        if parameters:
            if len(parameters) == 1:
                entities["parameter"] = parameters[0]
            else:
                entities["parameters"] = parameters
        
        # Extract region
        for region in REGIONS.keys():
            if region in text_lower:
                entities["region"] = region
                break
        
        # Extract cycle number
        cycle_match = re.search(r"cycle\s*(\d+)", text_lower)
        if cycle_match:
            entities["cycle_number"] = int(cycle_match.group(1))
        
        return entities
    
    # ========== LAYER 2: AI-ASSISTED ENTITY EXTRACTION ==========
    async def ai_extract_entities_only(self, query: str, context: dict) -> Dict[str, Any]:
        """AI extracts ONLY missing entities - LAYER 2"""
        try:
            prompt = f"""
            EXTRACT ONLY ENTITIES from this ARGO ocean data query. Return JSON with ONLY these fields if present:
            - float_id (integer)
            - parameter ("temperature", "salinity", or "pressure")  
            - region (from: {list(REGIONS.keys())})
            - cycle_number (integer)
            
            QUERY: "{query}"
            CONTEXT: {json.dumps(context, default=str)}
            
            Return ONLY JSON with extracted entities. Example:
            {{"float_id": 2901456, "parameter": "temperature"}}
            
            If no entities found, return empty object: {{}}
            """
            
            response = await asyncio.to_thread(
                lambda: self.mcp_server.gemini_model.generate_content(prompt)
            )
            result = json.loads(response.text.strip())
            logger.info(f"LAYER 2 - AI extracted entities: {result}")
            return result
            
        except Exception as e:
            logger.error(f"LAYER 2 - AI entity extraction failed: {e}")
            return {}
    
    # ========== LAYER 3: AI INTENT DETECTION ==========
    async def ai_detect_intent_entities(self, query: str, context: dict) -> Dict[str, Any]:
        """AI detects intent AND entities - LAYER 3"""
        try:
            available_intents = [
                "data_query", "profile_path", "profile_timeseries", "metadata_details",
                "semantic_search", "profile_comparison", "region_data", "data_export",
                "map_visualization", "list_floats", "cycle_data", "greeting", "farewell"
            ]
            
            prompt = f"""
            Detect intent and extract entities from this ARGO ocean data query.
            
            QUERY: "{query}"
            CONTEXT: {json.dumps(context, default=str)}
            AVAILABLE INTENTS: {available_intents}
            
            Return JSON:
            {{
                "intent": "detected_intent",
                "entities": {{"float_id": 123, "parameter": "temperature"}},
                "confidence": 0.85
            }}
            
            Confidence should be 0.0 to 1.0 based on how clear the intent is.
            """
            
            response = await asyncio.to_thread(
                lambda: self.mcp_server.gemini_model.generate_content(prompt)
            )
            result = json.loads(response.text.strip())
            logger.info(f"LAYER 3 - AI detected intent: {result}")
            return result
            
        except Exception as e:
            logger.error(f"LAYER 3 - AI intent detection failed: {e}")
            return {"intent": "unknown", "entities": {}, "confidence": 0.0}
    
    # ========== CONTEXT RESOLUTION ==========
    def resolve_context_references(self, entities: Dict[str, Any], context: dict) -> Dict[str, Any]:
        """Resolve pronouns and references using context"""
        resolved = entities.copy()
        
        # Handle pronoun resolution
        if 'float_id' not in resolved and 'last_float_id' in context:
            resolved['float_id'] = context['last_float_id']
            if 'float_ids' not in resolved:
                resolved['float_ids'] = [context['last_float_id']]
        
        if 'parameter' not in resolved and 'last_parameter' in context:
            resolved['parameter'] = context['last_parameter']
        
        if 'region' not in resolved and 'last_region' in context:
            resolved['region'] = context['last_region']
        
        return resolved

# ==================== HYBRID MCP SERVER ====================
class HybridArgoMCPServer:
    def __init__(self):
        self.db_pool = None
        self.collection = None
        self.gemini_model = None
        self.supabase = None
        self.sql_generator = None
        self.data_formatter = DataFormatter()
        self.memory = ConversationMemory()
        self.intent_processor = HybridIntentProcessor(self)
        
        # Execution budgets for safety
        self.execution_limits = {
            "max_tools_per_query": 3,
            "max_ai_calls_per_query": 2,
            "query_timeout": 30
        }
    
    # ==================== QUERY PROCESSING - 5-LAYER HYBRID APPROACH ====================
    async def process_query_hybrid(self, query: str, session_id: str) -> Dict[str, Any]:
        """
        MAIN HYBRID PROCESSING PIPELINE - 5 LAYERS
        """
        logger.info(f"HYBRID PROCESSING - Query: {query}, Session: {session_id}")
        
        # Get context from memory
        context = self.memory.get_context(session_id)
        
        # ========== LAYER 1: RULES-BASED PROCESSING ==========
        logger.info("LAYER 1: Rules-based processing")
        intent = self.intent_processor.detect_intent_rules(query)
        entities = self.intent_processor.extract_entities_rules(query)
        
        # Resolve context references
        entities = self.intent_processor.resolve_context_references(entities, context)
        
        if intent != "unknown" and self._has_required_entities(intent, entities):
            logger.info("LAYER 1 SUCCESS - Executing with rules only")
            result = await self.execute_mcp_tools(intent, entities)
            self.memory.add_exchange(session_id, query, result, intent, entities)
            return self._format_response(result, "rules_only", intent, 0.9)
        
        # ========== LAYER 2: AI-ASSISTED ENTITY EXTRACTION ==========
        logger.info("LAYER 2: AI-assisted entity extraction")
        if intent != "unknown" and not self._has_required_entities(intent, entities):
            ai_entities = await self.intent_processor.ai_extract_entities_only(query, context)
            combined_entities = {**entities, **ai_entities}
            combined_entities = self.intent_processor.resolve_context_references(combined_entities, context)
            
            if self._has_required_entities(intent, combined_entities):
                logger.info("LAYER 2 SUCCESS - Executing with AI entity help")
                result = await self.execute_mcp_tools(intent, combined_entities)
                self.memory.add_exchange(session_id, query, result, intent, combined_entities)
                return self._format_response(result, "ai_entity_assist", intent, 0.8)
        
        # ========== LAYER 3: AI INTENT DETECTION ==========
        logger.info("LAYER 3: AI intent detection")
        ai_analysis = await self.intent_processor.ai_detect_intent_entities(query, context)
        
        if ai_analysis.get("confidence", 0) > 0.7:
            detected_intent = ai_analysis["intent"]
            detected_entities = ai_analysis["entities"]
            detected_entities = self.intent_processor.resolve_context_references(detected_entities, context)
            
            if self._has_required_entities(detected_intent, detected_entities):
                logger.info("LAYER 3 SUCCESS - Executing with AI intent detection")
                result = await self.execute_mcp_tools(detected_intent, detected_entities)
                self.memory.add_exchange(session_id, query, result, detected_intent, detected_entities)
                return self._format_response(result, "ai_intent_detection", detected_intent, ai_analysis["confidence"])
        
        # ========== LAYER 4: COMPLEX AI ORCHESTRATION ==========
        logger.info("LAYER 4: Complex AI orchestration")
        complex_result = await self.process_complex_query(query, session_id)
        if complex_result and not complex_result.get("error"):
            logger.info("LAYER 4 SUCCESS - AI orchestration")
            self.memory.add_exchange(session_id, query, complex_result, "complex_ai", {})
            return self._format_response(complex_result, "ai_orchestration", "complex_ai", 0.6)
        
        # ========== LAYER 5: SQL GENERATION FALLBACK ==========
        logger.info("LAYER 5: SQL generation fallback")
        sql_result = await self.sql_generator.generate_sql_response(query, context)
        self.memory.add_exchange(session_id, query, sql_result, "sql_generation", {})
        
        if sql_result.get("success"):
            logger.info("LAYER 5 SUCCESS - SQL generation")
            return self._format_response(sql_result, "sql_generation", "custom_query", 0.5)
        else:
            # ULTIMATE FALLBACK - direct AI analysis
            logger.info("ULTIMATE FALLBACK - Direct AI analysis")
            analysis = await self.analyze_with_llm(query)
            fallback_result = {"ai_analysis": analysis, "note": "Used ultimate fallback"}
            return self._format_response(fallback_result, "emergency_fallback", "llm_chat", 0.1)
    
    def _has_required_entities(self, intent: str, entities: Dict[str, Any]) -> bool:
        """Enhanced entity checking with multi-parameter support"""
        required_entities = {
            "data_query": ["parameter"],
            "profile_path": ["float_id"],
            "profile_timeseries": ["float_id", "parameter"],
            "metadata_details": ["float_id"],
            "profile_comparison": ["float_ids"],
            "region_data": ["region"],
            "get_depth_profile": ["float_id", "parameter"],
            "get_trajectory": ["float_id"],
            "get_timeseries": ["float_id", "parameter"],
            "get_region_data": ["region"],
            "get_float_profile": ["float_id"],
            "get_float_trajectory": ["float_id"],
            "get_temporal_analysis": ["float_id", "parameter"],
            "compare_floats": ["float_ids"],
            "get_floats_in_region": ["region"],
            "greeting": [],
            "farewell": [],
        }
        
        if intent not in required_entities:
            return True
        
        required = required_entities[intent]
        return all(entity in entities and entities[entity] is not None for entity in required)
    
    def _format_response(self, result: Any, source: str, intent: str, confidence: float) -> Dict[str, Any]:
        """Format consistent response structure"""
        return {
            "result": result,
            "processing_source": source,
            "intent": intent,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat()
        }
    
    # ==================== ENHANCED MCP TOOLS EXECUTION ====================
    async def execute_mcp_tools(self, intent: str, entities: Dict[str, Any]) -> Any:
        """Enhanced MCP tool execution with greeting/farewell and compound tools"""
        
        # Handle greeting/farewell first
        if intent in ["greeting", "farewell"]:
            responses = {
                "greeting": "🌊 Hello! I'm your ARGO AI assistant! I can help you explore oceanographic data from ARGO floats. Ask me about temperature profiles, float trajectories, regional analysis, or complex ocean patterns!",
                "farewell": "👋 Goodbye! Feel free to come back anytime to explore more ARGO ocean data. Have a great day!"
            }
            return {"message": responses[intent]}
        
        # Enhanced tool mapping with compound tools
        if intent == "profile_comparison":
            if "parameters" in entities:
                return await self.compare_multiple_parameters(entities['float_ids'], entities['parameters'])
            else:
                return await self.compare_floats(entities['float_ids'], entities.get('parameter', 'temperature'))
        
        elif intent == "region_data":
            if "parameter" in entities:
                return await self.analyze_region_parameter(entities['region'], entities['parameter'])
            else:
                return await self.get_floats_in_region(entities['region'])
        
        # Standard tool mapping
        tool_mapping = {
            "data_query": self.query_measurements,
            "profile_path": self.get_float_trajectory,
            "profile_timeseries": self.get_timeseries,
            "metadata_details": self.get_float_profile,
            "get_depth_profile": self.get_depth_profile,
            "get_trajectory": self.get_trajectory,
            "get_timeseries": self.get_timeseries,
            "get_region_data": self.get_region_data,
            "semantic_search": self.search_floats_semantic,
            "location_search": self.search_floats_by_location,
            "list_floats": self.list_all_floats,
            "cycle_data": self.get_float_profile,
            "data_export": self.export_data_ascii,
            "get_temporal_analysis": self.get_temporal_analysis,
            "map_visualization": self.get_trajectory,  # Map visualization uses the trajectory data
            "count_metadata": self.count_floats,  # Count total floats and by institution
        }
        
        if intent in tool_mapping:
            tool = tool_mapping[intent]
            try:
                logger.info(f"Executing tool {tool.__name__} with entities: {entities}")
                result = await tool(**entities)
                logger.info(f"Tool execution result: {result}")
                if isinstance(result, dict) and "error" in result:
                    logger.error(f"Tool returned error: {result['error']}")
                return result
            except Exception as e:
                logger.error(f"Tool execution failed: {str(e)}", exc_info=True)
                return {"error": f"Tool execution failed: {str(e)}"}
        else:
            logger.error(f"No tool mapping for intent: {intent}")
            return {"error": f"No tool mapping for intent: {intent}"}
    
    async def count_floats(self) -> Dict:
        """Count total floats and breakdown by institution"""
        if not self.db_pool:
            return {"error": "Database not connected"}
            
        async with self.db_pool.acquire() as conn:
            try:
                # Get total count
                total_count = await conn.fetchval("""
                    SELECT COUNT(DISTINCT platform_number) 
                    FROM float_metadata
                """)
                
                # Get count by institution
                inst_counts = await conn.fetch("""
                    SELECT operating_institute, COUNT(*) as count
                    FROM float_metadata
                    GROUP BY operating_institute
                    ORDER BY count DESC
                """)
                
                # Get count by project
                proj_counts = await conn.fetch("""
                    SELECT project_name, COUNT(*) as count
                    FROM float_metadata
                    GROUP BY project_name
                    ORDER BY count DESC
                """)
                
                # Get active floats (with recent profiles)
                active_count = await conn.fetchval("""
                    SELECT COUNT(DISTINCT float_id) 
                    FROM profiles 
                    WHERE profile_date >= NOW() - INTERVAL '30 days'
                """)
                
                result = {
                    "total_floats": total_count,
                    "active_floats": active_count,
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
                            "total": total_count,
                            "active": active_count,
                            "institutions": len(inst_counts),
                            "projects": len(proj_counts)
                        }
                    }
                }
                
                return result
                
            except Exception as e:
                logger.error(f"Error counting floats: {str(e)}", exc_info=True)
                return {"error": f"Failed to count floats: {str(e)}"}

    # ==================== COMPOUND TOOLS ====================
    async def search_floats_by_location(self, latitude: float, longitude: float, radius: float = 5.0) -> Dict:
        """Search for floats near a specific latitude/longitude within a radius (in degrees)"""
        if not self.db_pool:
            return {"error": "Database not connected"}
            
        try:
            async with self.db_pool.acquire() as conn:
                # Find floats within the radius using Haversine formula
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
            
    async def analyze_region_parameter(self, region: str, parameter: str) -> Dict:
        """Compound tool: Get floats in region + analyze parameter"""
        try:
            # Step 1: Get floats in the region
            region_data = await self.get_floats_in_region(region)
            if isinstance(region_data, dict) and region_data.get("error"):
                return region_data
            
            float_ids = [float_data['platform_number'] for float_data in region_data.get('floats', [])]
            
            if not float_ids:
                return {"error": f"No floats found in {region} region"}
            
            # Step 2: Analyze parameter for each float
            region_analysis = {
                "region": region,
                "parameter": parameter,
                "total_floats": len(float_ids),
                "float_analyses": {},
                "regional_statistics": {}
            }
            
            values = []
            for float_id in float_ids[:5]:  # Limit to 5 floats for performance
                data = await self.query_measurements(float_id=float_id, parameter=parameter, limit=100)
                if data and not isinstance(data, dict):
                    param_values = [item.get(parameter) for item in data if item.get(parameter) is not None]
                    if param_values:
                        region_analysis["float_analyses"][float_id] = {
                            "data_points": len(param_values),
                            "average": sum(param_values) / len(param_values),
                            "min": min(param_values),
                            "max": max(param_values)
                        }
                        values.extend(param_values)
            
            # Step 3: Calculate regional statistics
            if values:
                region_analysis["regional_statistics"] = {
                    "total_measurements": len(values),
                    "regional_average": sum(values) / len(values),
                    "regional_min": min(values),
                    "regional_max": max(values),
                    "value_range": max(values) - min(values)
                }
            
            return region_analysis
            
        except Exception as e:
            return {"error": f"Regional analysis failed: {str(e)}"}
    
    async def compare_multiple_parameters(self, float_ids: List[int], parameters: List[str]) -> Dict:
        """Compare multiple parameters across floats"""
        try:
            comparison_result = {
                "float_ids": float_ids,
                "parameters": parameters,
                "comparisons": {}
            }
            
            for param in parameters:
                param_comparison = await self.compare_floats(float_ids, param)
                if not isinstance(param_comparison, dict) or param_comparison.get("error"):
                    continue
                    
                comparison_result["comparisons"][param] = param_comparison
            
            # Generate multi-parameter insights
            if comparison_result["comparisons"]:
                comparison_result["multi_parameter_insights"] = await self._generate_multi_param_insights(comparison_result)
            
            return comparison_result
            
        except Exception as e:
            return {"error": f"Multi-parameter comparison failed: {str(e)}"}
    
    async def _generate_multi_param_insights(self, comparison_data: Dict) -> str:
        """Generate AI insights for multi-parameter comparisons"""
        try:
            prompt = f"""
            Analyze this multi-parameter ARGO float comparison and provide key insights:
            
            {json.dumps(comparison_data, default=str)}
            
            Focus on:
            - Correlations between parameters
            - Notable patterns or anomalies
            - Which floats show interesting characteristics
            - Oceanographic significance
            
            Provide 3-4 key insights in bullet points.
            """
            
            response = await asyncio.to_thread(
                lambda: self.gemini_model.generate_content(prompt)
            )
            return response.text.strip()
        except Exception as e:
            return f"Insight generation failed: {str(e)}"
    
    # ==================== COMPLEX QUERY PROCESSING ====================
    async def process_complex_query(self, query: str, session_id: str) -> Dict:
        """LAYER 4: Complex query orchestration"""
        try:
            prompt = f"""
            Create an execution plan for this complex ARGO ocean data query.
            
            QUERY: "{query}"
            AVAILABLE TOOLS: {json.dumps(self.get_tool_list())}
            
            Return JSON execution plan:
            {{
                "plan": [
                    {{"tool": "tool_name", "parameters": {{"param": "value"}}}}
                ],
                "expected_output": "description of final result"
            }}
            """
            
            response = await asyncio.to_thread(
                lambda: self.gemini_model.generate_content(prompt)
            )
            plan_data = json.loads(response.text.strip())
            
            # Execute the plan
            results = await self._execute_plan(plan_data.get("plan", []))
            
            # Generate final response
            final_response = await self._generate_ai_response(query, results, plan_data.get("expected_output", ""))
            return final_response
            
        except Exception as e:
            logger.error(f"Complex query processing failed: {e}")
            return {"error": f"Complex processing failed: {str(e)}"}
    
    async def _execute_plan(self, plan: List[Dict]) -> Dict:
        """Execute multi-tool plan"""
        results = {}
        
        for step in plan[:self.execution_limits["max_tools_per_query"]]:
            try:
                tool_name = step['tool']
                parameters = step.get('parameters', {})
                
                if hasattr(self, tool_name):
                    result = await getattr(self, tool_name)(**parameters)
                    results[tool_name] = result
                else:
                    results[tool_name] = {"error": f"Tool {tool_name} not found"}
                    
            except Exception as e:
                logger.error(f"Tool execution failed for {tool_name}: {e}")
                results[tool_name] = {"error": str(e)}
        
        return results
    
    async def _generate_ai_response(self, original_query: str, tool_results: Dict, expected_output: str) -> Dict:
        """Generate AI response from tool results"""
        prompt = f"""
        Original Query: "{original_query}"
        Expected Output: "{expected_output}"
        
        Tool Results:
        {json.dumps(tool_results, default=str)}
        
        Create a comprehensive response that answers the original query using the tool results.
        """
        
        try:
            response = await asyncio.to_thread(
                lambda: self.gemini_model.generate_content(prompt)
            )
            return {"ai_synthesized_response": response.text, "tool_results": tool_results}
        except Exception as e:
            return {"error": "AI response generation failed", "tool_results": tool_results}
    
    # ==================== CORE MCP TOOLS - CORRECTED FOR CSV STRUCTURES ====================
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
                # Execute query
                rows = await conn.fetch(sql, *params)
                data = [dict(row) for row in rows]
                
                if not data:
                    return {"error": f"No data found for float {float_id} and parameter {parameter}"}
                
                # Format response with visualization
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
                            "x": parameter,
                            "y": "pressure",
                            "x_label": parameter.replace('_', ' ').title(),
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
            # Get metadata - UPDATED for CSV structure
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
            
            # Get measurement data - UPDATED for CSV structure
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
        """Get float trajectory - returns raw data"""
        if not self.db_pool:
            return {"error": "Database not connected"}
        
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
                return [dict(row) for row in rows]
            except Exception as e:
                logger.exception("Trajectory query error")
                err_msg = str(e) if str(e) else "Trajectory query failed; see server logs for traceback"
                return {"error": err_msg}
    
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
            
            df = pd.DataFrame(data)
            
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
                    return {"region": region, "floats": []}
                
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
                "float_count": len(comparison_data)
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
    
    # ==================== NEW DATA-FOCUSED TOOLS ====================
    async def get_depth_profile(self, float_id: int, cycle_number: Optional[int] = None, 
                              parameter: str = "temperature") -> Dict:
        """Get depth profile data for frontend plotting"""
        if parameter not in ['temperature', 'salinity', 'pressure', 'depth_m']:
            return {"error": f"Invalid parameter: {parameter}"}
        
        if cycle_number:
            data = await self.query_measurements(float_id=float_id, cycle_range=(cycle_number, cycle_number), limit=1000)
        else:
            data = await self.query_measurements(float_id=float_id, limit=1000)
        
        if isinstance(data, dict) and data.get("error"):
            return data
        
        formatted_data = self.data_formatter.format_depth_profile_data(data, parameter, float_id)
        
        return {
            "float_id": float_id,
            "cycle_number": cycle_number,
            "parameter": parameter,
            "data_points": len(data),
            "plot_data": formatted_data
        }
    
    async def get_trajectory(self, float_id: int) -> Dict:
        """Get trajectory data for frontend mapping"""
        try:
            logger.info(f"Getting trajectory for float {float_id}")
            data = await self.get_float_trajectory(float_id)
            
            if isinstance(data, dict) and data.get("error"):
                logger.error(f"Error getting trajectory: {data.get('error')}")
                return data
            
            if not data:
                logger.error(f"No trajectory data found for float {float_id}")
                return {"error": f"No trajectory data found for float {float_id}"}
            
            logger.info(f"Raw trajectory data: {data[:2]}...")  # Log first two points
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
            logger.info(f"Returning trajectory result with {len(data)} points")
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
                # Get total count first
                total_count = await conn.fetchval("SELECT COUNT(*) FROM float_metadata")
                
                # Get float data with location info
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
    
    # ==================== UTILITY METHODS ====================
    def get_tool_list(self) -> List[str]:
        """Get list of available MCP tools"""
        return [
            "query_measurements", "get_float_profile", "get_float_trajectory",
            "search_floats_semantic", "analyze_with_llm", "export_data_ascii",
            "get_floats_in_region", "compare_floats", "get_temporal_analysis",
            "get_depth_profile", "get_trajectory", "get_timeseries",
            "get_region_data", "list_all_floats", "process_complex_query",
            "analyze_region_parameter", "compare_multiple_parameters"
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
mcp_server = HybridArgoMCPServer()

# CORRECTED Database schema creation to match CSV structures
async def create_tables(conn):
    """Create database tables aligned with CSV file structures"""
    
    # Create float_metadata table (from FLOATS_METADATA.csv)
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
    
    # Create profiles table (from PROFILES.csv)
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
    
    # Create measurements table (from your text data)
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
    
    # Create indexes for better performance
    await conn.execute("CREATE INDEX IF NOT EXISTS measurements_float_id_idx ON measurements(float_id);")
    await conn.execute("CREATE INDEX IF NOT EXISTS measurements_cycle_idx ON measurements(cycle_number);")
    await conn.execute("CREATE INDEX IF NOT EXISTS profiles_float_id_idx ON profiles(float_id);")
    await conn.execute("CREATE INDEX IF NOT EXISTS profiles_cycle_idx ON profiles(cycle_number);")
    
    logger.info("Database tables and indexes checked/created successfully.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting ARGO AI Hybrid System - Raw Data API...")
    
    # Create database connection pool
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

    # Initialize Gemini model
    genai.configure(api_key=GEMINI_API_KEY)
    app.state.gemini_model = genai.GenerativeModel("gemini-2.5-flash")
    await mcp_server.set_gemini_model(app.state.gemini_model)

    # Setup ChromaDB
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    app.state.chroma = chromadb.PersistentClient(path="./chroma_db")
    app.state.collection = app.state.chroma.get_or_create_collection(
        name="argo_metadata", embedding_function=ef
    )
    await mcp_server.set_collection(app.state.collection)

    # Setup Supabase for SQL generation
    app.state.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    await mcp_server.set_supabase(app.state.supabase)

    # Create database tables
    if app.state.pool:
        async with app.state.pool.acquire() as conn:
            await create_tables(conn)

    yield
    
    # Graceful shutdown
    logger.info("Shutting down ARGO AI Hybrid System...")
    if hasattr(app.state, 'pool') and app.state.pool:
        await app.state.pool.close()
        logger.info("Database pool closed successfully")

app = FastAPI(
    title="ARGO AI Hybrid System - Raw Data API",
    description="Complete ARGO oceanographic data system returning raw data for frontend visualization",
    version="10.0.0",
    lifespan=lifespan
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ==================== API ENDPOINTS ====================
@app.get("/")
async def root():
    return {
        "message": "🌊 ARGO AI Hybrid System - Raw Data API v10.0",
        "status": "ready",
        "features": [
            "✅ 5-Layer Hybrid Processing",
            "✅ Raw Data for Frontend Visualization", 
            "✅ Structured JSON Responses",
            "✅ No Base64 Images - Pure Data",
            "✅ Frontend-Friendly Formatting",
            "✅ Enhanced Regional Analysis",
            "✅ Multi-Parameter Comparison",
            "✅ Semantic Search Capabilities"
        ],
        "data_formats": [
            "Depth Profiles: {depths: [], values: []}",
            "Trajectory Maps: {trajectories: [{points: []}]}",
            "Time Series: {dates: [], values: []}",
            "Regional Data: {institution_counts: {}, map_data: []}",
            "Comparison Data: {comparison: {}, statistics: {}}"
        ],
        "mcp_tools": mcp_server.get_tool_list(),
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
    """Main query endpoint using 5-layer hybrid processing - returns raw data"""
    query = payload.get("query", "").strip()
    session_id = payload.get("session_id", str(uuid.uuid4()))
    
    if not query:
        raise HTTPException(status_code=400, detail="Query text required")
    
    logger.info(f"Processing query: {query} (session: {session_id})")
    
    try:
        result = await mcp_server.process_query_hybrid(query, session_id)

        # If the tool returned an inner error object, propagate as HTTP error so frontend shows message
        inner = result.get("result") if isinstance(result, dict) else None
        if isinstance(inner, dict) and "error" in inner:
            detail = inner.get("error") or "Query failed; see server logs for details"
            raise HTTPException(status_code=404, detail=detail)

        # Flatten inner result into top-level so frontend finds viz/data directly
        if isinstance(inner, dict):
            merged = {**result}
            # Merge inner keys into top-level (inner wins)
            merged.update(inner)
            merged.pop("result", None)
            merged["session_id"] = session_id
            merged["query"] = query
            return merged

        # Fallback: return original structure with session metadata
        return {
            **result,
            "session_id": session_id,
            "query": query
        }
    except Exception as e:
        logger.error(f"Query processing failed: {e}")
        # Ultimate fallback
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

@app.get("/mcp/tools")
async def get_mcp_tools():
    """Get information about available MCP tools"""
    tools_info = [
        {
            "name": "query_measurements",
            "description": "Query ARGO measurements with various filters",
            "parameters": ["float_id", "parameter", "depth_range", "cycle_range", "limit"],
            "returns": "Raw measurement data"
        },
        {
            "name": "get_float_profile", 
            "description": "Get complete profile for a specific float including metadata",
            "parameters": ["float_id", "cycle_number"],
            "returns": "Float metadata and measurements"
        },
        {
            "name": "get_float_trajectory",
            "description": "Get trajectory data for a specific float",
            "parameters": ["float_id"],
            "returns": "Latitude/longitude points"
        },
        {
            "name": "search_floats_semantic",
            "description": "Semantic search for floats based on natural language query",
            "parameters": ["query", "n_results"],
            "returns": "Semantically similar floats"
        },
        {
            "name": "get_depth_profile",
            "description": "Get depth profile data for frontend plotting",
            "parameters": ["float_id", "cycle_number", "parameter"],
            "returns": "Structured depth profile data"
        },
        {
            "name": "get_trajectory", 
            "description": "Get trajectory data for frontend mapping",
            "parameters": ["float_id"],
            "returns": "Structured map trajectory data"
        },
        {
            "name": "get_timeseries",
            "description": "Get time series data for frontend plotting", 
            "parameters": ["float_id", "parameter"],
            "returns": "Structured time series data"
        },
        {
            "name": "get_region_data",
            "description": "Get region data for frontend visualization",
            "parameters": ["region"],
            "returns": "Structured regional analysis data"
        },
        {
            "name": "compare_floats",
            "description": "Compare multiple floats based on a specific parameter",
            "parameters": ["float_ids", "parameter"],
            "returns": "Comparison statistics and data"
        },
    ]
    
    return {
        "total_tools": len(tools_info),
        "tools": tools_info,
        "data_emphasis": "All tools return structured raw data for frontend visualization"
    }

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)