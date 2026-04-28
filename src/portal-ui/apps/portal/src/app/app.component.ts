import { Component, OnInit } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { NavShellComponent } from './layout/nav-shell/nav-shell.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, NavShellComponent],
  template: `
    <orbit-nav-shell>
      <router-outlet />
    </orbit-nav-shell>
  `
})
export class AppComponent {}
