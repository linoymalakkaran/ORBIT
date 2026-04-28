import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../apps/portal/src/environments/environment';

@Injectable({ providedIn: 'root' })
export class ProjectsApiService {
  private http = inject(HttpClient);
  private base = `${environment.apiBaseUrl}/api/projects`;

  list(page = 1, size = 20, program?: string, status?: string): Observable<any> {
    let params = new HttpParams().set('page', page).set('size', size);
    if (program) params = params.set('program', program);
    if (status)  params = params.set('status', status);
    return this.http.get<any>(this.base, { params });
  }

  getById(id: string): Observable<any> { return this.http.get<any>(`${this.base}/${id}`); }

  create(body: any): Observable<any> { return this.http.post<any>(this.base, body); }

  update(id: string, body: any): Observable<any> { return this.http.put<any>(`${this.base}/${id}`, body); }

  archive(id: string): Observable<void> { return this.http.delete<void>(`${this.base}/${id}`); }
}

@Injectable({ providedIn: 'root' })
export class ArtifactsApiService {
  private http = inject(HttpClient);
  private url(pid: string) { return `${environment.apiBaseUrl}/api/projects/${pid}/artifacts`; }

  list(projectId: string): Observable<any>  { return this.http.get<any>(this.url(projectId)); }
  getById(projectId: string, id: string): Observable<any> {
    return this.http.get<any>(`${this.url(projectId)}/${id}`);
  }
  upload(projectId: string, body: any): Observable<any> {
    return this.http.post<any>(this.url(projectId), body);
  }
}

@Injectable({ providedIn: 'root' })
export class ApprovalsApiService {
  private http = inject(HttpClient);
  private base = `${environment.apiBaseUrl}/api/approvals`;

  list(artifactId: string): Observable<any> {
    return this.http.get<any>(`${this.base}?artifactId=${artifactId}`);
  }
  submit(artifactId: string, body: any): Observable<any> {
    return this.http.post<any>(`${this.base}?artifactId=${artifactId}`, body);
  }
}

@Injectable({ providedIn: 'root' })
export class TeamApiService {
  private http = inject(HttpClient);
  private url(pid: string) { return `${environment.apiBaseUrl}/api/projects/${pid}/team`; }

  list(projectId: string): Observable<any[]> { return this.http.get<any[]>(this.url(projectId)); }
  add(projectId: string, body: any): Observable<void> { return this.http.post<void>(this.url(projectId), body); }
  remove(projectId: string, userId: string): Observable<void> {
    return this.http.delete<void>(`${this.url(projectId)}/${userId}`);
  }
}

@Injectable({ providedIn: 'root' })
export class LedgerApiService {
  private http = inject(HttpClient);
  private base = `${environment.apiBaseUrl}/api/ledger`;

  byProject(projectId: string, page = 1): Observable<any> {
    return this.http.get<any>(`${this.base}?projectId=${projectId}&page=${page}`);
  }
  verify(projectId: string): Observable<any> {
    return this.http.get<any>(`${this.base}/verify?projectId=${projectId}`);
  }
}

@Injectable({ providedIn: 'root' })
export class ContextApiService {
  private http = inject(HttpClient);
  private url(pid: string) { return `${environment.apiBaseUrl}/api/context/${pid}`; }

  getThread(projectId: string): Observable<any[]> {
    return this.http.get<any[]>(this.url(projectId));
  }
  append(projectId: string, message: string): Observable<any[]> {
    return this.http.post<any[]>(this.url(projectId), { message });
  }
}
