/**
 *Centralized, typed Query Key Factory for React Query.
 *
 * Invariant: Every workspace-scoped query MUST include workspaceId as a key segment
 * to ensure strict tenant isolation in cache and prevent cross-tenant data leakage.
 */
export const queryKeys = {
  auth: {
    me: ['auth', 'me'] as const,
  },
  workspaces: {
    all: ['workspaces'] as const,
    detail: (workspaceId: string) => ['workspaces', workspaceId] as const,
    members: (workspaceId: string) => ['workspaces', workspaceId, 'members'] as const,
    memberDetail: (workspaceId: string, memberId: string) =>
      ['workspaces', workspaceId, 'members', memberId] as const,
    invitations: (workspaceId: string) => ['workspaces', workspaceId, 'invitations'] as const,
    clients: (workspaceId: string) => ['workspaces', workspaceId, 'clients'] as const,
    clientDetail: (workspaceId: string, clientId: string) =>
      ['workspaces', workspaceId, 'clients', clientId] as const,
    projects: (workspaceId: string) => ['workspaces', workspaceId, 'projects'] as const,
    projectDetail: (workspaceId: string, projectId: string) =>
      ['workspaces', workspaceId, 'projects', projectId] as const,
    projectMembers: (workspaceId: string, projectId: string) =>
      ['workspaces', workspaceId, 'projects', projectId, 'members'] as const,
  },
} as const;
