import { useState } from 'preact/hooks'
export default function Counter() {
  const [n, setN] = useState(0)
  return <button onClick={() => setN(n + 1)}>{`count: ${n}`}</button>
}
