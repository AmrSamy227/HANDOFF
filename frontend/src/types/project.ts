import { WorkspaceMemberUser } from './workspace';

export type ProjectStatus =
  | 'planning'
  | 'in_progress'
  | 'in_review'
  | 'changes_requested'
  | 'approved'
  | 'completed'
  | 'archived';

export type ProjectMemberRole = 'lead' | 'collaborator' | 'reviewer' | 'client';

export interface Client {
  id: string;
  workspace: string;
  name: string;
  contact_email: string;
  contact_phone: string;
  company_website: string;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface Project {
  id: string;
  workspace: string;
  client: string | null;
  client_name: string | null;
  name: string;
  description: string;
  status: ProjectStatus;
  start_date: string | null;
  deadline: string | null;
  created_by: WorkspaceMemberUser | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectMember {
  id: string;
  project: string;
  user: WorkspaceMemberUser;
  role: ProjectMemberRole;
  created_at: string;
}

// Request Payloads
export interface CreateClientPayload {
  name: string;
  contact_email?: string;
  contact_phone?: string;
  company_website?: string;
  notes?: string;
}

export interface UpdateClientPayload {
  name?: string;
  contact_email?: string;
  contact_phone?: string;
  company_website?: string;
  notes?: string;
}

export interface CreateProjectPayload {
  name: string;
  client?: string | null;
  description?: string;
  status?: ProjectStatus;
  start_date?: string | null;
  deadline?: string | null;
}

export interface UpdateProjectPayload {
  name?: string;
  client?: string | null;
  description?: string;
  status?: ProjectStatus;
  start_date?: string | null;
  deadline?: string | null;
}

export interface AddProjectMemberPayload {
  user_id: string;
  role: ProjectMemberRole;
}

export interface UpdateProjectMemberPayload {
  role: ProjectMemberRole;
}
