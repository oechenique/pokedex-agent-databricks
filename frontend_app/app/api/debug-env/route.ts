// Diagnóstico temporal (esqueleto de validación, reglas/07-estado-actual.md):
// nunca devuelve VALORES, solo nombres de env vars, para descubrir qué
// inyecta Databricks Apps en runtime de Node -- necesario para saber cómo
// pedir un token del service principal propio de esta app, igual que
// mcp_client.py hace con WorkspaceClient() en Python.
export async function GET() {
  const keys = Object.keys(process.env).sort();
  return Response.json({ keys });
}
