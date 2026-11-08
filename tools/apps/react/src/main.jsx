import { useState } from 'react'
import { createRoot } from 'react-dom/client'
function Counter() {
  const [n, setN] = useState(0)
  return <button onClick={() => setN(n + 1)}>count: {n}</button>
}
createRoot(document.getElementById('app')).render(<Counter />)
