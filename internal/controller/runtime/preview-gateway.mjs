import http from 'node:http'
import net from 'node:net'
import fs from 'node:fs'
import { execFileSync } from 'node:child_process'

/** Route only this worktree's exact browser hosts, over a loopback-only SSH endpoint. */
const meta = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'))
const services = meta.project_profile.services
const routes = new Map(services.filter((service) => service.http !== false)
  .map((service) => [new URL(meta.preview_urls[service.name]).host, service]))

/** Return current branch identity without embedding user changes or credentials. */
function identity() {
  return {
    project: meta.project_profile.name,
    task: meta.task_id,
    machine: meta.machine_id,
    branch: execFileSync('git', ['branch', '--show-current'], { cwd: meta.cwd, encoding: 'utf8' }).trim(),
    commit: execFileSync('git', ['rev-parse', 'HEAD'], { cwd: meta.cwd, encoding: 'utf8' }).trim(),
  }
}

/** Reject cross-preview origins; API CORS is granted only to this task's frontend. */
function accepted(req, service) {
  if (!service) return false
  const origin = req.headers.origin
  return !origin || Object.values(meta.preview_urls).includes(origin)
}

/** Proxy HTTP and attach branch evidence; no access logs or request bodies are recorded. */
const server = http.createServer((req, res) => {
  const service = routes.get(req.headers.host)
  if (!accepted(req, service)) { res.writeHead(403).end('Unknown preview host or origin'); return }
  if (req.url === '/__box_worker') {
    res.writeHead(200, { 'content-type': 'application/json', 'cache-control': 'no-store' })
    res.end(JSON.stringify(identity())); return
  }
  const headers = { ...req.headers }
  const origin = headers.origin
  if (service.api_cors_origin && origin) headers.origin = service.api_cors_origin
  const upstream = http.request({ hostname: '127.0.0.1', port: meta.service_ports[service.name],
    method: req.method, path: req.url, headers }, (reply) => {
    const outgoing = { ...reply.headers, 'x-box-project': meta.project_profile.name, 'x-box-task': meta.task_id }
    if (service.api_cors_origin && origin) {
      outgoing['access-control-allow-origin'] = origin
      outgoing['access-control-allow-credentials'] = 'true'
      outgoing.vary = 'Origin'
    }
    res.writeHead(reply.statusCode, outgoing)
    reply.pipe(res)
  })
  upstream.on('error', () => { if (!res.headersSent) res.writeHead(502); res.end('Project service is restarting; retry shortly.') })
  req.pipe(upstream)
})

/** Carry Vite HMR WebSockets without changing their host, path, cookies or payloads. */
server.on('upgrade', (req, socket, head) => {
  const service = routes.get(req.headers.host)
  if (!accepted(req, service)) { socket.destroy(); return }
  const upstream = net.connect(meta.service_ports[service.name], '127.0.0.1', () => {
    const headers = Object.entries(req.headers).map(([key, value]) => `${key}: ${value}`).join('\r\n')
    upstream.write(`${req.method} ${req.url} HTTP/${req.httpVersion}\r\n${headers}\r\n\r\n`)
    if (head.length) upstream.write(head)
    socket.pipe(upstream).pipe(socket)
  })
  upstream.on('error', () => socket.destroy())
  socket.on('error', () => upstream.destroy())
  socket.on('close', () => upstream.destroy())
})

server.listen(meta.gateway_port, '127.0.0.1')
