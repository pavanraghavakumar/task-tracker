export type Priority = 'low' | 'medium' | 'high';
export type TaskStatus = 'pending' | 'in_progress' | 'completed';

export interface User { id: number; name: string; email: string; created_at: string; }
export interface Category { id: number; name: string; color: string; task_count?: number; }
export interface Task {
  id: number; title: string; description: string; category: Category | null;
  priority: Priority; status: TaskStatus; due_date: string | null;
  completed_at: string | null; created_at: string; updated_at: string;
}
export interface TaskInput { title: string; description: string; category_id: number | null; priority: Priority; status: TaskStatus; due_date: string | null; }
export interface TaskFilters { search?: string; status?: string; priority?: string; category_id?: number; sort_by?: string; sort_order?: 'asc' | 'desc'; page?: number; per_page?: number; }
export interface DashboardStats { total: number; pending: number; in_progress: number; completed: number; overdue: number; completion_rate: number; upcoming_deadlines: Task[]; }
export interface ApiResponse<T> { success: true; data: T; message?: string; }
export interface Paginated<T> { items: T[]; pagination: { page: number; per_page: number; total: number; pages: number; }; }
export interface AuthData { access_token: string; user: User; }
