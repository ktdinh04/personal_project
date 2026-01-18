"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Puzzle,
  RefreshCw,
  Search,
  CheckCircle,
  AlertCircle,
  Clock,
  Settings,
  Power,
  PowerOff,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { cn, getStatusColor, getStatusBgColor } from "@/lib/utils";
import type { Module } from "@/types";
import { useAuth } from "@/hooks/use-auth";
import { useToast } from "@/hooks/use-toast";

const statusIcons: Record<string, typeof CheckCircle> = {
  healthy: CheckCircle,
  unhealthy: AlertCircle,
  error: AlertCircle,
  starting: Clock,
  stopped: PowerOff,
  unknown: Puzzle,
};

export default function ModulesPage() {
  const [modules, setModules] = useState<Module[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [reloading, setReloading] = useState(false);
  const { user } = useAuth();
  const { toast } = useToast();

  const loadModules = async () => {
    try {
      const response = await api.getModules(true);
      setModules(response.items);
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to load modules",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadModules();
  }, []);

  const handleReloadModules = async () => {
    setReloading(true);
    try {
      await api.reloadModules();
      await loadModules();
      toast({
        title: "Modules Reloaded",
        description: "Module registry has been refreshed",
        variant: "success",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to reload modules",
        variant: "destructive",
      });
    } finally {
      setReloading(false);
    }
  };

  const handleToggleModule = async (module: Module) => {
    try {
      if (module.is_enabled) {
        await api.disableModule(module.module_id);
      } else {
        await api.enableModule(module.module_id);
      }
      await loadModules();
      toast({
        title: module.is_enabled ? "Module Disabled" : "Module Enabled",
        description: `${module.name} has been ${module.is_enabled ? "disabled" : "enabled"}`,
        variant: "success",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to toggle module",
        variant: "destructive",
      });
    }
  };

  const filteredModules = modules.filter(
    (m) =>
      m.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.tags.some((t) => t.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <Skeleton className="h-8 w-48" />
            <Skeleton className="h-4 w-64 mt-2" />
          </div>
          <Skeleton className="h-10 w-40" />
        </div>
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-64" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Module Registry</h1>
          <p className="text-muted-foreground mt-1">
            Manage and configure installed modules
          </p>
        </div>
        {user?.is_admin && (
          <Button onClick={handleReloadModules} disabled={reloading}>
            <RefreshCw className={cn("mr-2 h-4 w-4", reloading && "animate-spin")} />
            Reload Modules
          </Button>
        )}
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Search modules..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-9"
        />
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Modules</p>
                <p className="text-2xl font-bold">{modules.length}</p>
              </div>
              <Puzzle className="h-8 w-8 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Enabled</p>
                <p className="text-2xl font-bold text-green-500">
                  {modules.filter((m) => m.is_enabled).length}
                </p>
              </div>
              <Power className="h-8 w-8 text-green-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Healthy</p>
                <p className="text-2xl font-bold text-green-500">
                  {modules.filter((m) => m.status === "healthy").length}
                </p>
              </div>
              <CheckCircle className="h-8 w-8 text-green-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Issues</p>
                <p className="text-2xl font-bold text-red-500">
                  {modules.filter((m) => m.status === "unhealthy" || m.status === "error").length}
                </p>
              </div>
              <AlertCircle className="h-8 w-8 text-red-500" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Empty State */}
      {filteredModules.length === 0 && (
        <Card className="py-12">
          <CardContent className="flex flex-col items-center justify-center text-center">
            <Puzzle className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold">No modules found</h3>
            <p className="text-muted-foreground mt-2 max-w-md">
              {searchQuery
                ? "No modules match your search. Try a different query."
                : "No modules are installed. Add modules to the modules directory."}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Module Grid */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {filteredModules.map((module, index) => {
          const StatusIcon = statusIcons[module.status] || Puzzle;

          return (
            <motion.div
              key={module.module_id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
            >
              <Card
                className={cn(
                  "h-full flex flex-col",
                  !module.is_enabled && "opacity-60"
                )}
              >
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <CardTitle className="flex items-center gap-2">
                        {module.name}
                        <Badge variant="outline" className="text-xs">
                          v{module.version}
                        </Badge>
                      </CardTitle>
                      <CardDescription className="mt-1">
                        {module.description || "No description"}
                      </CardDescription>
                    </div>
                  </div>
                </CardHeader>

                <CardContent className="flex-1">
                  {/* Status */}
                  <div className="flex items-center gap-2 mb-4">
                    <div
                      className={cn(
                        "flex items-center gap-1 px-2 py-1 rounded-full text-xs",
                        getStatusBgColor(module.status),
                        getStatusColor(module.status)
                      )}
                    >
                      <StatusIcon className="h-3 w-3" />
                      {module.status}
                    </div>
                    <Badge variant={module.is_enabled ? "default" : "secondary"}>
                      {module.is_enabled ? "Enabled" : "Disabled"}
                    </Badge>
                  </div>

                  {/* Tags */}
                  {module.tags && module.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-4">
                      {module.tags.map((tag) => (
                        <Badge key={tag} variant="outline" className="text-xs">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  )}

                  {/* Paths */}
                  <div className="text-xs text-muted-foreground space-y-1">
                    {module.ui_path && (
                      <p>UI: {module.ui_path}</p>
                    )}
                    {module.api_base_path && (
                      <p>API: {module.api_base_path}</p>
                    )}
                  </div>
                </CardContent>

                {/* Actions */}
                {user?.is_admin && (
                  <div className="p-4 pt-0 flex gap-2">
                    <Button
                      variant={module.is_enabled ? "destructive" : "default"}
                      size="sm"
                      className="flex-1"
                      onClick={() => handleToggleModule(module)}
                    >
                      {module.is_enabled ? (
                        <>
                          <PowerOff className="mr-2 h-3 w-3" />
                          Disable
                        </>
                      ) : (
                        <>
                          <Power className="mr-2 h-3 w-3" />
                          Enable
                        </>
                      )}
                    </Button>
                    <Button variant="outline" size="sm">
                      <Settings className="h-3 w-3" />
                    </Button>
                  </div>
                )}
              </Card>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
