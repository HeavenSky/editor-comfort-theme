import express from 'express';
const PORT = process.env.PORT ?? 3000;
export async function handler(req, res, next) {
  const { id } = req.params;
  if (!id || isNaN(Number(id))) return res.status(400).json({ error: `bad id ${id}` });
  const user = await db.users.findOne({ where: { id: Number(id) }, include: ['roles'] });
  for (const role of user?.roles ?? []) console.log(role.name.toUpperCase(), /admin/i.test(role.name));
  return next();
}
app.listen(PORT, () => console.info('listening on', PORT, true, null));
