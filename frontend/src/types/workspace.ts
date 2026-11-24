export type WorkspaceType = 'personal' | 'agency';

export type WorkspaceMemberRole = 'owner' | 'admin' | 'member' | 'client';

export type WorkspaceMemberStatus = 'active' | 'suspended';

export type WorkspaceInvitationRole = 'admin' | 'member' | 'client';

export type WorkspaceInvitationStatus = 'pending' | 'accepted' | 'revoked' | 'expired';

export interface WorkspaceMemberUser {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  avatar: string | null;
}

export interface WorkspaceClientMinimal {
  id: string;
  name: string;
}

export interface Workspace {
  id: string;
  name: string;
  slug: string;
  workspace_type: WorkspaceType;
  owner: WorkspaceMemberUser;
  logo: string | null;
  member_count: number;
  user_role: WorkspaceMemberRole | null;
  created_at: string;
  updated_at: string;
}

export interface WorkspaceMember {
  id: string;
  workspace: string;
  user: WorkspaceMemberUser;
  role: WorkspaceMemberRole;
  status: WorkspaceMemberStatus;
  client: string | null;
  client_detail: WorkspaceClientMinimal | null;
  joined_at: string;
}

export interface WorkspaceInvitation {
  id: string;
  workspace: string;
  email: string;
  role: WorkspaceInvitationRole;
  client: string | null;
  invited_by: WorkspaceMemberUser;
  status: WorkspaceInvitationStatus;
  raw_token?: string; // Only returned on creation (201 response)
  expires_at: string;
  created_at: string;
  accepted_at: string | null;
}

// Request Payloads
export interface CreateWorkspacePayload {
  name: string;
  workspace_type?: WorkspaceType;
  logo?: File | null;
}

export interface UpdateWorkspacePayload {
  name?: string;
  workspace_type?: WorkspaceType;
  logo?: File | null;
}

export interface TransferOwnershipPayload {
  new_owner_id: string;
}

export interface UpdateWorkspaceMemberPayload {
  role?: WorkspaceInvitationRole;
  status?: WorkspaceMemberStatus;
  client?: string | null;
}

export interface CreateWorkspaceInvitationPayload {
  email: string;
  role: WorkspaceInvitationRole;
  client?: string | null;
}

export interface AcceptInvitationPayload {
  token: string;
}
