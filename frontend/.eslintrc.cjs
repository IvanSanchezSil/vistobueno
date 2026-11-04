// Config ESLint real: `npm run lint` (antes no había configuración y el script fallaba).
module.exports = {
  root: true,
  env: { browser: true, es2021: true },
  extends: ['eslint:recommended', 'plugin:react/recommended', 'plugin:react/jsx-runtime', 'plugin:react-hooks/recommended'],
  parserOptions: { ecmaVersion: 'latest', sourceType: 'module' },
  settings: { react: { version: 'detect' } },
  plugins: ['react'],
  ignorePatterns: ['dist/', 'node_modules/'],
  overrides: [
    {
      // El archivo de configuración del build corre en Node, no en el
      // navegador: necesita `process` y el resto de globales de Node.
      // El patrón es relativo a la raíz del frontend: no habilita Node en
      // el código de `src/`, que sí corre en el navegador.
      files: ['vite.config.js'],
      env: { node: true },
    },
  ],
  rules: {
    'react/prop-types': 'off',
    'no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
  },
}
