import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import TerminalEntry from "./TerminalEntry";
import type { TerminalTask } from "../api/types";

const base:TerminalTask={task_id:"t1",instruction:"查看电脑内存",status:"awaiting_confirmation",created_at:"now",plan_hash:"a".repeat(64),expires_at:"2030-01-01T00:00:00Z",
  plan:{goal:"读取物理内存容量",cwd:"/tmp/example-project",relative_dir:".",impact:"可能读写",risk:"low",warnings:["命令以当前用户账号运行"],requires_risk_ack:true,requires_high_risk_ack:false,requires_network_ack:false,environment:{PATH:"/usr/bin"},
    steps:[{kind:"exec",description:"读取物理内存",executable:"/usr/sbin/sysctl",args:["-n","hw.memsize"],command:"/usr/sbin/sysctl -n hw.memsize",timeout_seconds:30,risk:"low",risk_reason:"常见只读查询"}]}};

const render=(task:TerminalTask)=>renderToStaticMarkup(<TerminalEntry task={task} busy={false} onConfirm={vi.fn()} onCancel={vi.fn()} onReplan={vi.fn()}/>);

describe("TerminalEntry",()=>{
  it("renders request, command and a y/n confirmation prompt",()=>{
    const html=render(base);
    expect(html).toContain("查看电脑内存");expect(html).toContain("你");expect(html).toContain("AI");
    expect(html).toContain("sysctl -n hw.memsize");expect(html).toContain("执行目录");
    expect(html).toContain("需要你确认才执行");expect(html).toContain("<kbd>y</kbd>");
    expect(html).toContain("执行 (y)");expect(html).toContain("取消 (n)");
    expect(html).toContain("无 OS 沙箱");
  });

  it("shows raw output, exit code, port facts and AI summary separately",()=>{
    const html=render({...base,status:"completed",summary:"物理内存 48 GiB",steps:[{step_index:0,status:"completed",stdout:"51539607552\n",stderr:"",exit_code:0}]});
    expect(html).toContain("51539607552");expect(html).toContain("[exit 0]");expect(html).toContain("物理内存 48 GiB");
    expect(html).toContain("AI");expect(html).not.toContain("执行 (y)");
    const port=render({...base,status:"completed",summary:"",steps:[{step_index:0,status:"completed",stdout:"",stderr:"",exit_code:1,facts:{port:8092,protocol:"TCP",listening:false,processes:[],scope:"当前用户可见范围"}}]});
    expect(port).toContain("8092");expect(port).toContain("未发现 TCP 监听");expect(port).toContain("[exit 1]");
  });

  it("marks failure, cancellation and replanning without pretending success",()=>{
    const html=render({...base,status:"failed",error:"Exit 1: permission denied",steps:[{step_index:0,status:"failed",stdout:"",stderr:"permission denied",exit_code:1,error:"命令退出码非零"}]});
    expect(html).toContain("permission denied");expect(html).toContain("重新规划");expect(html).toContain("[exit 1]");
    const cancelled=render({...base,status:"cancelled"});
    expect(cancelled).toContain("重新规划");
  });

  it("shows a planning state before any command exists",()=>{
    const html=render({...base,status:"planning",plan:null,expires_at:null});
    expect(html).toContain("正在理解需求并生成命令");
    expect(html).not.toContain("执行 (y)");
  });
});
