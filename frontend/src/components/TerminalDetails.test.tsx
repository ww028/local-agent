import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import type { TerminalTask } from "../api/types";
import TerminalDetails from "./TerminalDetails";

const base:TerminalTask={task_id:'synthetic',instruction:'检查状态',status:'awaiting_confirmation',created_at:'2026-01-01',expires_at:'2026-01-01',plan_hash:'synthetic',plan:{goal:'检查',cwd:'/synthetic/project',relative_dir:'.',impact:'只读',environment:{},steps:[{action:'git_status',description:'Git状态',executable:'/usr/bin/git',args:['status'],command:'/usr/bin/git status',timeout_seconds:30}]},steps:[]};
function render(changes:Partial<TerminalTask>={}){return renderToStaticMarkup(<TerminalDetails task={{...base,...changes}} busy={false} onConfirm={()=>{}} onCancel={()=>{}} onReplan={()=>{}}/>);}
describe('confirmed terminal review',()=>{
  it('shows exact command and directory before confirmation',()=>{
    const html=render();expect(html).toContain('/usr/bin/git status');expect(html).toContain('/synthetic/project');expect(html).toContain('确认执行以上命令');expect(html).toContain('尚未执行');
  });
  it('does not offer confirmation for executed or expired plans',()=>{
    expect(render({status:'completed'})).not.toContain('确认执行以上命令');
    const html=render({status:'expired'});expect(html).not.toContain('确认执行以上命令');expect(html).toContain('需再次确认');
  });
  it('shows factual output and AI explanation separately without HTML execution',()=>{
    const html=render({status:'completed',summary:'AI explanation',steps:[{step_index:0,status:'completed',exit_code:0,stdout:'<script>bad</script>',stderr:''}]});
    expect(html).toContain('事实记录');expect(html).toContain('AI结果解释');expect(html).toContain('退出码');expect(html).not.toContain('<script>');expect(html).toContain('&lt;script&gt;');
  });
  it('keeps failed output and offers replanning instead of auto rerun',()=>{
    const html=render({status:'failed',error:'Nonzero exit'});expect(html).toContain('Nonzero exit');expect(html).toContain('重新规划');expect(html).not.toContain('确认执行以上命令');
  });
});
