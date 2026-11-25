# 本地稳定运行技术方案

## 目标

开发仍支持Vite热更新；日常体验不依赖开发服务器。已构建React静态资源由
同一个FastAPI单worker承载，减少用户需要管理的进程、Origin差异和热更新干扰。
Ollama仍独立本地服务，启动脚本可发现已有服务，无账号或开机项。

## 实现

- FastAPI增加静态assets挂载及SPA路由回退，只在静态构建存在时启用。
- API未匹配不能回退成HTML；阻止../路径，构建资源只读。
- `scripts/start.sh` 检查依赖/已构建文件，若未构建提示setup；启动Ollama
  仅在loopback探测不可用时，设置禁云/单并发，stdout日志在ignored data；
  然后单backend进程提供Web与API在8000。退出只清理由此脚本创建的服务。
- `scripts/setup.sh`安装后前端build；后续离线启动不触发npm/pip下载。
- 用户现有5173开发入口保留，日常可用8000。默认不改系统PATH和登录项。

## 验收

没有dist时不假装可用；构建后/、/documents及assets加载正常，/api/unknown
404而非HTML；Host/Origin保护保持；端口已有服务不盲目再起；模型缺失界面
提示；启动脚本bash语法/真实HTTP冒烟和浏览器加载。此为本地打包运行形态，
不意味着企业公网生产部署。
