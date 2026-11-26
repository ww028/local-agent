import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import TerminalEntry from "./TerminalEntry";
import type { TerminalTask } from "../api/types";

const base:TerminalTask={task_id:"t1",instruction:"查看电脑内存",status:"awaiting_confirmation",created_at:"now",plan_hash:"a".repeat(64),expires_at:"2030-01-01T00:00:00Z",
  plan:{goal:"读取物理内存容量",cwd:"/tmp/example-project",relative_dir:".",impact:"可能写入或覆盖文件",risk:"high",warnings:["命令以当前用户账号运行"],effects:["可能写入或覆盖文件"],auto_run:false,requires_risk_ack:true,requires_high_risk_ack:true,requires_network_ack:false,environment:{PATH:"/usr/bin"},
    steps:[{kind:"shell",description:"写入合成文件",executable:"/bin/bash",args:[],command:"printf x > made.txt",timeout_seconds:30,risk:"high",risk_reason:"会写入文件"}]}};

const render=(task:TerminalTask)=>renderToStaticMarkup(<TerminalEntry task={task} busy={false} onConfirm={vi.fn()} onCancel={vi.fn()} onReplan={vi.fn()}/>);

describe("TerminalEntry",()=>{
  it("explains the impact in plain words and folds the command away",()=>{
    const html=render(base);
    expect(html).toContain("查看电脑内存");expect(html).toContain("你");expect(html).toContain("AI");
    expect(html).toContain("需要你确认后才执行");
    expect(html).toContain("执行后会有这些影响");
    expect(html).toContain("可能写入或覆盖文件");
    expect(html).toContain("执行 (y)");expect(html).toContain("取消 (n)");expect(html).toContain("<kbd>y</kbd>");
    expect(html).toContain("查看即将执行的命令");
    expect(html).toContain("<details"); // commands stay behind a disclosure
  });

  it("shows read-only plans auto-ran without a confirmation card",()=>{
    const html=render({...base,status:"completed",digest:"48 GiB",summary:"物理内存为 48 GiB。",plan:{...base.plan!,effects:["只读取信息，不会修改文件或系统设置"],auto_run:true,requires_high_risk_ack:false,steps:[{kind:"exec",description:"读取物理内存",executable:"/usr/sbin/sysctl",args:["-n","hw.memsize"],command:"/usr/sbin/sysctl -n hw.memsize",timeout_seconds:30}]},steps:[{step_index:0,status:"completed",stdout:"51539607552\n",stderr:"",exit_code:0}]});
    expect(html).toContain("只读查询 · 已自动执行");
    expect(html).toContain("结果");expect(html).toContain("48 GiB");
    expect(html).not.toContain("执行 (y)");expect(html).not.toContain("需要你确认后才执行");
  });

  it("puts the key result first and keeps raw output folded",()=>{
    const html=render({...base,status:"completed",digest:"arm64 · Apple Silicon",summary:"你的电脑是 Apple Silicon。",steps:[{step_index:0,status:"completed",stdout:"arm64\n",stderr:"",exit_code:0}]});
    expect(html).toContain("arm64 · Apple Silicon");expect(html).toContain("查看原始输出");
    const order=html.indexOf("结果")<html.indexOf("查看原始输出");
    expect(order).toBe(true);
    expect(html).not.toContain("执行 (y)");
    const port=render({...base,status:"completed",summary:"",steps:[{step_index:0,status:"completed",stdout:"",stderr:"",exit_code:1,facts:{port:8092,protocol:"TCP",listening:false,processes:[],scope:"当前用户可见范围"}}]});
    expect(port).toContain("8092");expect(port).toContain("未发现 TCP 监听");
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
