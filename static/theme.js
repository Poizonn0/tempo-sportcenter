(() => {
  const storageKey = "sportcenter-theme";
  let theme = "light";

  try {
    theme = localStorage.getItem(storageKey) === "dark" ? "dark" : "light";
  } catch (_error) {
    // The site still works with the light theme if browser storage is disabled.
  }

  const root = document.documentElement;
  root.dataset.theme = theme;
  root.style.colorScheme = theme;

  document.addEventListener("DOMContentLoaded", () => {
    const toggle = document.getElementById("theme-toggle");
    if (!toggle) return;

    const updateButton = () => {
      const dark = root.dataset.theme === "dark";
      toggle.textContent = dark ? "☼" : "☾";
      toggle.setAttribute("aria-label", dark ? "Включить светлую тему" : "Включить тёмную тему");
      toggle.title = dark ? "Светлая тема" : "Тёмная тема";
    };

    updateButton();
    toggle.addEventListener("click", () => {
      theme = root.dataset.theme === "dark" ? "light" : "dark";
      root.dataset.theme = theme;
      root.style.colorScheme = theme;
      try {
        localStorage.setItem(storageKey, theme);
      } catch (_error) {
        // Theme switching remains available until this page is closed.
      }
      updateButton();
    });
  });
})();
