<script setup>
const n = ref(0)
</script>
<template>
  <main>
    <h1>Counter</h1>
    <button @click="n++">count: {{ n }}</button>
  </main>
</template>
