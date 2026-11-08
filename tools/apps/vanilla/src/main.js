let n = 0
const b = document.createElement('button')
const r = () => (b.textContent = 'count: ' + n)
b.onclick = () => { n++; r() }
r()
document.getElementById('app').append(b)
