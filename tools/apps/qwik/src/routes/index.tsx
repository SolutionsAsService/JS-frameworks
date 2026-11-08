import { component$, useSignal } from "@builder.io/qwik";

export default component$(() => {
  const n = useSignal(0);
  return (
    <main>
      <h1>Counter</h1>
      <button onClick$={() => n.value++}>{`count: ${n.value}`}</button>
    </main>
  );
});
