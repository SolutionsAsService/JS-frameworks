import { Component, signal } from '@angular/core';

@Component({
  selector: 'app-root',
  template: `<h1>Counter</h1><button (click)="n.set(n() + 1)">count: {{ n() }}</button>`,
})
export class App {
  protected readonly n = signal(0);
}
