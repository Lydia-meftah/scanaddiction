/** Tailwind compilé (remplace cdn.tailwindcss.com).
 * Régénérer après modification des classes :
 *   npx tailwindcss@3.4.17 -i css/tailwind.src.css -o css/tailwind.css --minify
 */
module.exports = {
  content: ['./*.html', './js/**/*.js'],
  theme: { extend: {} },
  plugins: [],
};
