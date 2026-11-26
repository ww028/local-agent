import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import MessageBubble from "./MessageBubble";

function render(content: string) {
  return renderToStaticMarkup(<MessageBubble message={{id:1,role:"assistant",content,status:"complete"}} />);
}
describe("offline Markdown rendering",()=>{
  it("renders math, tables and code locally",()=>{
    const html=render('$a^2+b^2=c^2$\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n```js\nconst x = 1;\n```');
    expect(html).toContain('katex');
    expect(html).toContain('<table>');
    expect(html).toContain('hljs');
  });
  it("does not render raw HTML or remote images",()=>{
    const html=render('<script>alert(1)</script>\n\n![remote](https://example.com/photo.png)');
    expect(html).not.toContain('<script>');
    expect(html).not.toContain('<img');
    expect(html).not.toContain('src="https://');
  });
  it("does not turn model hyperlinks into navigation",()=>{
    expect(render('[outside](https://example.com)')).not.toContain('href="https://');
  });
});
