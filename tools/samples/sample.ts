import { readFile } from "node:fs/promises";

export const LIMIT = 10;
/** 文档注释 @param name 名称 */
export async function greet(name: string, count = 2): Promise<string> {
  const items: number[] = [1, 2, 3];
  const re = /^a+\d$/g;
  let text = `hello ${name}, ${items.length} items`;
  if (typeof name === "string" && count > LIMIT) throw new Error("bad");
  return text + (await readFile("a.txt", "utf8")) + console.log(re);
}
