// Wait for the DOM to load
document.addEventListener('DOMContentLoaded', () => {
  const rootElement = document.documentElement;
  const themeToggleButton = document.getElementById('theme-toggle');

  // Set the theme and update the toggle button text
  function setTheme(theme) {
    rootElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    themeToggleButton.textContent = theme === 'dark' ? 'Light Mode' : 'Dark Mode';
  }

  // Get the stored theme or default to light
  const storedTheme = localStorage.getItem('theme') || 'light';
  setTheme(storedTheme);

  // Toggle theme on button click
  if (themeToggleButton) {
    themeToggleButton.addEventListener('click', () => {
      const currentTheme = rootElement.getAttribute('data-theme');
      const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
      setTheme(newTheme);
    });
  }

  // Additional dynamic behaviors can be added here.
});
