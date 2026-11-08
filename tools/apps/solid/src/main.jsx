import { createSignal } from 'solid-js'
import { render } from 'solid-js/web'
function Counter() {
  const [n, setN] = createSignal(0)
  return <button onClick={() => setN(n() + 1)}>count: {n()}</button>
}
render(() => <Counter />, document.getElementById('app'))
