import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map, Observable } from 'rxjs';
import { ApiResponse, AuthData, Category, DashboardStats, Paginated, Task, TaskFilters, TaskInput } from './models';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = '/api/v1';
  private unwrap<T>() { return map((response: ApiResponse<T>) => response.data); }

  login(payload: { email: string; password: string }): Observable<AuthData> { return this.http.post<ApiResponse<AuthData>>(`${this.baseUrl}/auth/login`, payload).pipe(this.unwrap<AuthData>()); }
  register(payload: { name: string; email: string; password: string }): Observable<AuthData> { return this.http.post<ApiResponse<AuthData>>(`${this.baseUrl}/auth/register`, payload).pipe(this.unwrap<AuthData>()); }
  dashboard(): Observable<DashboardStats> {
    return this.http.get<ApiResponse<{ counts: Omit<DashboardStats, 'completion_rate' | 'upcoming_deadlines'>; completion_percentage: number; upcoming_deadlines: Task[] }>>(`${this.baseUrl}/dashboard`).pipe(
      this.unwrap(),
      map(({ counts, completion_percentage, upcoming_deadlines }) => ({ ...counts, completion_rate: completion_percentage, upcoming_deadlines })),
    );
  }
  tasks(filters: TaskFilters): Observable<Paginated<Task>> {
    let params = new HttpParams();
    for (const [key, value] of Object.entries(filters)) if (value !== undefined && value !== '') params = params.set(key, value);
    return this.http.get<ApiResponse<Paginated<Task>>>(`${this.baseUrl}/tasks`, { params }).pipe(this.unwrap<Paginated<Task>>());
  }
  task(id: number): Observable<Task> { return this.http.get<ApiResponse<Task>>(`${this.baseUrl}/tasks/${id}`).pipe(this.unwrap<Task>()); }
  createTask(payload: TaskInput): Observable<Task> { return this.http.post<ApiResponse<Task>>(`${this.baseUrl}/tasks`, payload).pipe(this.unwrap<Task>()); }
  updateTask(id: number, payload: TaskInput | Partial<TaskInput>): Observable<Task> { return this.http.patch<ApiResponse<Task>>(`${this.baseUrl}/tasks/${id}`, payload).pipe(this.unwrap<Task>()); }
  deleteTask(id: number): Observable<void> { return this.http.delete<ApiResponse<void>>(`${this.baseUrl}/tasks/${id}`).pipe(this.unwrap<void>()); }
  categories(): Observable<Category[]> { return this.http.get<ApiResponse<Category[]>>(`${this.baseUrl}/categories`).pipe(this.unwrap<Category[]>()); }
  createCategory(payload: { name: string; color: string }): Observable<Category> { return this.http.post<ApiResponse<Category>>(`${this.baseUrl}/categories`, payload).pipe(this.unwrap<Category>()); }
  updateCategory(id: number, payload: { name: string; color: string }): Observable<Category> { return this.http.patch<ApiResponse<Category>>(`${this.baseUrl}/categories/${id}`, payload).pipe(this.unwrap<Category>()); }
  deleteCategory(id: number): Observable<void> { return this.http.delete<ApiResponse<void>>(`${this.baseUrl}/categories/${id}`).pipe(this.unwrap<void>()); }
}
