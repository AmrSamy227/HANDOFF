'use client';

import React, { createContext, useContext, useMemo } from 'react';
import { useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { Workspace, WorkspaceMemberRole } from '@/types/workspace';
import { queryKeys } from './query-keys';
import { api } from './api';
import { useAuth } from './auth-context';

export interface WorkspaceContextType {
  // Current active workspace state (URL is the single source of truth)
  workspaceId: string | null;
  workspace: Workspace | null;
  isLoading: boolean;
  isError: boolean;
  error: Error | null;

  // Role and convenience permission flags derived from active workspace data
  userRole: WorkspaceMemberRole | null;
  isOwner: boolean;
  isAdmin: boolean;
  isMember: boolean;
  isClient: boolean;

  // User's workspaces list
  workspaces: Workspace[];
  isLoadingWorkspaces: boolean;
  refetchWorkspaces: () => Promise<unknown>;
}

const WorkspaceContext = createContext<WorkspaceContextType | undefined>(undefined);

/**
 * Hook to fetch all workspaces accessible by the current user.
 */
export function useWorkspaces() {
  const { user } = useAuth();

  const query = useQuery({
    queryKey: queryKeys.workspaces.all,
    queryFn: ({ signal }) => api.get<Workspace[]>('/api/v1/workspaces/', { signal }),
    enabled: Boolean(user),
  });

  return {
    workspaces: query.data ?? [],
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error as Error | null,
    refetch: query.refetch,
  };
}

/**
 * Hook to fetch and derive state for a specific workspace.
 * Invariant: Does not silently select a fallback when workspaceId is invalid/inaccessible.
 */
export function useWorkspace(workspaceId?: string | null) {
  const { user } = useAuth();
  const validId = workspaceId && workspaceId.trim().length > 0 ? workspaceId : null;

  const query = useQuery({
    queryKey: validId ? queryKeys.workspaces.detail(validId) : ['workspaces', 'noop'],
    queryFn: ({ signal }) => api.get<Workspace>(`/api/v1/workspaces/${validId}/`, { signal }),
    enabled: Boolean(validId) && Boolean(user),
  });

  const workspace = query.data ?? null;
  const userRole = workspace?.user_role ?? null;

  return {
    workspace,
    isLoading: validId ? query.isLoading : false,
    isError: validId ? query.isError : false,
    error: query.error as Error | null,
    userRole,
    isOwner: userRole === 'owner',
    isAdmin: userRole === 'owner' || userRole === 'admin',
    isMember: userRole === 'member',
    isClient: userRole === 'client',
    refetch: query.refetch,
  };
}

/**
 * WorkspaceProvider resolves the active workspace from props or URL route params.
 * Server state is managed exclusively by React Query; no state duplication occurs.
 */
export function WorkspaceProvider({
  children,
  workspaceId: propWorkspaceId,
}: {
  children: React.ReactNode;
  workspaceId?: string | null;
}) {
  const params = useParams();
  const routeWorkspaceId = params?.workspaceId as string | undefined;
  const resolvedWorkspaceId = propWorkspaceId ?? routeWorkspaceId ?? null;

  const {
    workspace,
    isLoading,
    isError,
    error,
    userRole,
    isOwner,
    isAdmin,
    isMember,
    isClient,
  } = useWorkspace(resolvedWorkspaceId);

  const {
    workspaces,
    isLoading: isLoadingWorkspaces,
    refetch: refetchWorkspaces,
  } = useWorkspaces();

  const contextValue = useMemo<WorkspaceContextType>(
    () => ({
      workspaceId: resolvedWorkspaceId,
      workspace,
      isLoading,
      isError,
      error,
      userRole,
      isOwner,
      isAdmin,
      isMember,
      isClient,
      workspaces,
      isLoadingWorkspaces,
      refetchWorkspaces,
    }),
    [
      resolvedWorkspaceId,
      workspace,
      isLoading,
      isError,
      error,
      userRole,
      isOwner,
      isAdmin,
      isMember,
      isClient,
      workspaces,
      isLoadingWorkspaces,
      refetchWorkspaces,
    ]
  );

  return (
    <WorkspaceContext.Provider value={contextValue}>
      {children}
    </WorkspaceContext.Provider>
  );
}

/**
 * Hook to consume active workspace context.
 */
export function useActiveWorkspace() {
  const context = useContext(WorkspaceContext);
  if (!context) {
    throw new Error('useActiveWorkspace must be used within a WorkspaceProvider');
  }
  return context;
}
