import { LitElement, html } from 'lit'
class MyCounter extends LitElement {
  static properties = { n: { type: Number } }
  constructor() { super(); this.n = 0 }
  render() { return html`<button @click=${() => this.n++}>count: ${this.n}</button>` }
}
customElements.define('my-counter', MyCounter)
document.getElementById('app').appendChild(document.createElement('my-counter'))
