import React, { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ChevronLeft, ChevronRight, Search, Database, Download } from "lucide-react";

interface DataTableProps {
  data: any[];
}

export const DataTable: React.FC<DataTableProps> = ({ data }) => {
  const [currentPage, setCurrentPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState("");
  const [itemsPerPage] = useState(10);

  if (!data || data.length === 0) {
    return (
      <Card>
        <CardContent className="p-6 text-center text-muted-foreground">
          No data available to display
        </CardContent>
      </Card>
    );
  }

  // Get column headers from the first object
  const columns = Object.keys(data[0]);
  
  // Filter data based on search term
  const filteredData = data.filter(row =>
    Object.values(row).some(value =>
      value?.toString().toLowerCase().includes(searchTerm.toLowerCase())
    )
  );

  // Calculate pagination
  const totalItems = filteredData.length;
  const totalPages = Math.ceil(totalItems / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const currentData = filteredData.slice(startIndex, endIndex);

  const formatValue = (value: any, key: string) => {
    if (value === null || value === undefined) return "-";
    
    // Format numbers based on column type
    if (typeof value === 'number') {
      if (key.includes('lat') || key.includes('lon') || key.includes('temperature') || key.includes('salinity')) {
        return value.toFixed(3);
      }
      if (key.includes('pressure')) {
        return value.toFixed(1);
      }
      return value.toString();
    }
    
    // Format dates
    if (key.includes('date') || key.includes('time')) {
      try {
        return new Date(value).toLocaleString();
      } catch {
        return value.toString();
      }
    }
    
    return value.toString();
  };

  const getColumnType = (key: string) => {
    const lowerKey = key.toLowerCase();
    if (lowerKey.includes('id')) return 'ID';
    if (lowerKey.includes('lat') || lowerKey.includes('lon')) return 'Coordinate';
    if (lowerKey.includes('temp')) return 'Temperature';
    if (lowerKey.includes('sal')) return 'Salinity';
    if (lowerKey.includes('press')) return 'Pressure';
    if (lowerKey.includes('date') || lowerKey.includes('time')) return 'Date';
    return 'Text';
  };

  const getColumnColor = (type: string) => {
    switch (type) {
      case 'ID': return 'bg-primary/5 text-primary';
      case 'Coordinate': return 'bg-accent/5 text-accent';
      case 'Temperature': return 'bg-warning/5 text-warning';
      case 'Salinity': return 'bg-success/5 text-success';
      case 'Pressure': return 'bg-destructive/5 text-destructive';
      case 'Date': return 'bg-secondary/5 text-secondary-foreground';
      default: return 'bg-muted/5 text-muted-foreground';
    }
  };

  const exportCsv = () => {
    const rows = filteredData;
    const header = columns.join(",");
    const escape = (val: any) => {
      if (val == null) return "";
      const s = String(val).replace(/"/g, '""');
      return /[",\n]/.test(s) ? `"${s}"` : s;
    };
    const body = rows.map((row) => columns.map((c) => escape(row[c])).join(",")).join("\n");
    const csv = header + "\n" + body;
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `data_export_${Date.now()}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(a.href);
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center space-x-2">
            <Database className="h-5 w-5 text-primary" />
            <span>Data Table</span>
            <Badge variant="secondary" className="ml-2">
              {totalItems} records
            </Badge>
          </CardTitle>
          <div className="flex items-center space-x-2">
            <Button variant="outline" size="sm" onClick={exportCsv}>
              <Download className="h-4 w-4 mr-2" />
              Export
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search data..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setCurrentPage(1);
              }}
              className="pl-10"
            />
          </div>

          {/* Table */}
          <div className="rounded-lg border overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/5">
                  {columns.map((column) => {
                    const columnType = getColumnType(column);
                    return (
                      <TableHead key={column} className="font-semibold">
                        <div className="flex items-center space-x-2">
                          <span className="capitalize">
                            {column.replace(/_/g, ' ')}
                          </span>
                          <Badge 
                            variant="outline" 
                            className={`text-xs ${getColumnColor(columnType)}`}
                          >
                            {columnType}
                          </Badge>
                        </div>
                      </TableHead>
                    );
                  })}
                </TableRow>
              </TableHeader>
              <TableBody>
                {currentData.map((row, index) => (
                  <TableRow key={index} className="hover:bg-muted/5">
                    {columns.map((column) => (
                      <TableCell key={column} className="font-mono text-sm">
                        {formatValue(row[column], column)}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between">
              <div className="text-sm text-muted-foreground">
                Showing {startIndex + 1} to {Math.min(endIndex, totalItems)} of {totalItems} records
              </div>
              <div className="flex items-center space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                  disabled={currentPage === 1}
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <span className="text-sm">
                  Page {currentPage} of {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                  disabled={currentPage === totalPages}
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};
