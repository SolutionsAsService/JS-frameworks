import { render } from 'preact'
import { useState } from 'preact/hooks'
function Counter() {
  const [n, setN] = useState(0)
  return <button onClick={() => setN(n + 1)}>count: {n}</button>
}
render(<Counter />, document.getElementById('app'))
