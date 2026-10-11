import { useEffect, useMemo, useRef, useState } from 'react'
import { Canvas, ThreeEvent, useFrame, useThree } from '@react-three/fiber'
import { Html, OrbitControls, RoundedBox, useCursor } from '@react-three/drei'
import * as THREE from 'three'
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib'

export type WorldAgent = { id: string; name?: string; role: string; status: string; category_id?: string; last_activity_at?: string | null; tagId?: string }
export type WorldCategory = { id: string; name: string; color: string; built_in?: boolean }
export type WorldWorkload = { running_jobs?: number; queued_jobs?: number; running_since?: string | null }
export type WorldInteraction = { id: string; interaction_id?: string; from_agent_id: string; to_agent_id: string; status: string; started_at?: string; completed_at?: string; kind?: string }
export type WorldProps = {
  agents: WorldAgent[]
  selected: string | null
  onSelect: (agentId: string) => void
  reducedMotion: boolean
  resetKey: number
  active?: boolean
  categories?: WorldCategory[]
  workloads?: Record<string, WorldWorkload>
  interactions?: WorldInteraction[]
}

type Role = 'hr' | 'finance' | 'support' | 'security' | 'optimizer' | 'custom'
type Point = [number, number, number]
const ZONES: Array<{ role: Role; label: string; subtitle: string; position: Point; color: string }> = [
  { role: 'hr', label: 'HR', subtitle: 'POLICY & PEOPLE', position: [-5.5, 0, 2.6], color: '#63c8bd' },
  { role: 'finance', label: 'Finance', subtitle: 'INVOICE INTELLIGENCE', position: [-5.5, 0, -2.35], color: '#ac9dea' },
  { role: 'support', label: 'Support', subtitle: 'CUSTOMER OPERATIONS', position: [-.15, 0, -3.2], color: '#91b6ce' },
  { role: 'security', label: 'Security', subtitle: 'PERMISSION GUARDIAN', position: [5.2, 0, -2.35], color: '#d7b583' },
  { role: 'optimizer', label: 'Optimizer', subtitle: 'WORKLOAD ORCHESTRATION', position: [5.2, 0, 2.6], color: '#72bda9' },
]
const SLATE = '#24313e'
const WHITE = '#e5e9e7'
const CAMERA_POSITION: Point = [10, 9.5, 15]
const CAMERA_TARGET: Point = [-.15, .35, -.1]
const ROLE_NAME: Record<Role, string> = { hr: 'HR', finance: 'Finance', support: 'Support', security: 'Security', optimizer: 'Optimizer', custom: 'Custom' }
const normalizeRole = (role: string): string => {
  const value = role.toLowerCase()
  if (value.includes('hr') || value.includes('human')) return 'hr'
  if (value.includes('finance') || value.includes('invoice')) return 'finance'
  if (value.includes('support')) return 'support'
  if (value.includes('security') || value.includes('guardian')) return 'security'
  if (value.includes('optim')) return 'optimizer'
  return value
}
const agentSeed = (id: string) => Array.from(id).reduce((hash, char) => (hash * 31 + char.charCodeAt(0)) >>> 0, 0)
const agentRole = (agent: WorldAgent): Role => ZONES.find(zone => zone.role === normalizeRole(agent.role))?.role ?? 'custom'
const agentColor = (agent: WorldAgent, categoryColor?: string): string => {
  const base = new THREE.Color(categoryColor ?? ZONES.find(zone => zone.role === agentRole(agent))?.color ?? '#94bdd0')
  const hsl = { h: 0, s: 0, l: 0 }
  base.getHSL(hsl)
  const seed = agentSeed(agent.id)
  return base.setHSL(hsl.h + (seed % 11 - 5) * .004, THREE.MathUtils.clamp(hsl.s + (seed % 7 - 3) * .018, .2, .65), THREE.MathUtils.clamp(hsl.l + (seed % 9 - 4) * .012, .35, .73)).getStyle()
}

function SoftBox({ position = [0, 0, 0], size, color = SLATE, radius = .08, ...props }: {
  position?: Point; size: Point; color?: string; radius?: number; rotation?: Point; emissive?: string; intensity?: number
}) {
  return <RoundedBox position={position} rotation={props.rotation} args={size} radius={Math.min(radius, ...size.map(n => n / 2 - .001))} smoothness={3} castShadow receiveShadow>
    <meshStandardMaterial color={color} roughness={.55} metalness={.13} emissive={props.emissive ?? '#000000'} emissiveIntensity={props.intensity ?? 0} />
  </RoundedBox>
}

function Ball({ position, radius, color = WHITE, scale, emissive, intensity = 0 }: {
  position: Point; radius: number; color?: string; scale?: Point; emissive?: string; intensity?: number
}) {
  return <mesh position={position} scale={scale} castShadow>
    <sphereGeometry args={[radius, 20, 16]} />
    <meshStandardMaterial color={color} roughness={.62} metalness={.03} emissive={emissive ?? '#000'} emissiveIntensity={intensity} />
  </mesh>
}

function Cable({ points, color = '#46616b', radius = .018, emissive = false }: { points: Point[]; color?: string; radius?: number; emissive?: boolean }) {
  const geometry = useMemo(() => new THREE.TubeGeometry(new THREE.CatmullRomCurve3(points.map(p => new THREE.Vector3(...p))), 32, radius, 5, false), [points, radius])
  useEffect(() => () => geometry.dispose(), [geometry])
  return <mesh geometry={geometry}>
    <meshStandardMaterial color={color} emissive={color} emissiveIntensity={emissive ? .5 : .03} roughness={.6} />
  </mesh>
}

function Plant({ position, size = 1 }: { position: Point; size?: number }) {
  return <group position={position} scale={size}>
    <mesh position={[0, .24, 0]} castShadow>
      <cylinderGeometry args={[.27, .2, .46, 16]} />
      <meshStandardMaterial color="#59606a" roughness={.7} />
    </mesh>
    <mesh position={[0, .48, 0]}><cylinderGeometry args={[.235, .235, .025, 16]} /><meshStandardMaterial color="#25372d" /></mesh>
    {Array.from({ length: 7 }, (_, i) => {
      const angle = i * Math.PI * 2 / 7
      return <group key={i} rotation={[Math.sin(angle) * .48, angle, Math.cos(angle) * .45]} position={[0, .52, 0]}>
        <mesh position={[0, .25, 0]} castShadow><capsuleGeometry args={[.09, .38, 4, 8]} /><meshStandardMaterial color={i % 2 ? '#729e87' : '#517968'} roughness={.85} /></mesh>
      </group>
    })}
  </group>
}

function Monitor({ position = [0, 1.13, -.55], accent, security = false }: { position?: Point; accent: string; security?: boolean }) {
  return <group position={position}>
    <SoftBox size={[.08, .35, .1]} position={[0, -.15, 0]} color="#52616c" radius={.025} />
    <SoftBox size={[.53, .06, .32]} position={[0, -.32, .05]} color="#53616d" radius={.03} />
    <SoftBox size={[1.13, .72, .075]} color="#4c5c68" radius={.055} />
    <SoftBox size={[1.01, .60, .02]} position={[0, 0, .046]} color="#122630" radius={.035} />
    <SoftBox size={[.06, .055, .012]} position={[-.41, .22, .063]} color={accent} emissive={accent} intensity={.65} radius={.01} />
    <SoftBox size={[.45, .036, .012]} position={[-.13, .22, .063]} color="#71868c" radius={.009} />
    {Array.from({ length: 4 }, (_, i) => <SoftBox key={i} size={[security ? .68 - i * .12 : .22 + i * .13, .03, .012]} position={[-.33 + i * .05, .08 - i * .105, .063]} color={i === 1 ? accent : '#4b6470'} radius={.005} emissive={i === 1 ? accent : undefined} intensity={.25} />)}
    <SoftBox size={[.21, .31, .012]} position={[.33, -.05, .063]} color="#203d45" radius={.02} />
    {[.13, .18, .1].map((h, i) => <SoftBox key={i} size={[.035, h, .013]} position={[.27 + i * .065, -.14 + h / 2, .077]} color={accent} radius={.006} emissive={accent} intensity={.35} />)}
  </group>
}

function Desk({ accent, role }: { accent: string; role: Role }) {
  return <group position={[0, 0, -.57]}>
    <SoftBox size={[2.6, .18, 1.35]} position={[0, .86, 0]} color="#63717a" radius={.085} />
    <SoftBox size={[2.44, .025, 1.19]} position={[0, .965, 0]} color="#829099" radius={.05} />
    {[-.94, .94].map(x => <SoftBox key={x} size={[.15, .83, .77]} position={[x, .39, 0]} color="#344450" radius={.025} />)}
    <SoftBox size={[2.12, .055, .038]} position={[0, .85, .675]} color={accent} emissive={accent} intensity={.33} radius={.012} />
    <Monitor accent={accent} security={role === 'security'} />
    <SoftBox size={[.75, .035, .29]} position={[.15, .999, .40]} color="#3a4e5a" radius={.027} />
    {[0, 1, 2].map(row => <SoftBox key={row} size={[.62, .006, .012]} position={[.15, 1.022, .33 + row * .073]} color="#8898a0" radius={.002} />)}
    <SoftBox size={[.19, .065, .26]} position={[.74, 1.015, .43]} color="#ced4d0" radius={.04} />
    <mesh position={[-.83, 1.075, .26]} castShadow><cylinderGeometry args={[.1, .08, .2, 12]} /><meshStandardMaterial color={accent} roughness={.65} /></mesh>
    <mesh position={[-.83, 1.18, .26]}><cylinderGeometry args={[.085, .085, .007, 12]} /><meshStandardMaterial color="#263a38" /></mesh>
    {role === 'finance' && <group position={[-.78, .98, -.26]}>
      {[0, 1, 2, 3].map(i => <SoftBox key={i} size={[.43, .025, .42]} position={[i * .01, i * .027, 0]} color="#e1e1d5" radius={.013} />)}
      <SoftBox size={[.28, .009, .025]} position={[0, .115, -.1]} color={accent} radius={.004} />
    </group>}
    {role === 'hr' && <group position={[.88, 1.01, -.37]} rotation={[0, -.2, 0]}>
      <SoftBox size={[.34, .09, .45]} color={accent} radius={.025} />
      <SoftBox size={[.28, .05, .41]} position={[.015, 0, 0]} color="#d9ddd1" radius={.01} />
    </group>}
  </group>
}

function FilingCabinet({ position, accent }: { position: Point; accent: string }) {
  return <group position={position}>
    <SoftBox size={[.75, 1.32, .63]} position={[0, .66, 0]} color="#3c4e5b" />
    {[0, 1, 2].map(i => <group key={i} position={[0, .24 + i * .42, .33]}>
      <SoftBox size={[.62, .33, .025]} color="#60717c" radius={.025} />
      <SoftBox size={[.2, .028, .05]} position={[0, .015, .032]} color="#b8c6c6" radius={.01} />
      <SoftBox size={[.09, .04, .01]} position={[-.17, -.07, .027]} color={accent} radius={.006} />
    </group>)}
    <Plant position={[0, 1.34, 0]} size={.55} />
  </group>
}

function MessageWall({ accent }: { accent: string }) {
  return <group position={[0, .2, -1.7]}>
    <SoftBox size={[2.45, 1.46, .12]} position={[0, 1.22, 0]} color="#334450" radius={.075} />
    <SoftBox size={[2.22, 1.19, .025]} position={[0, 1.22, .073]} color="#152731" radius={.035} />
    {[-.72, 0, .72].map((x, i) => <group key={i} position={[x, 1.26, .1]}>
      <SoftBox size={[.58, .59, .012]} color={i === 1 ? '#2d4851' : '#243b47'} radius={.045} />
      <Ball position={[-.15, .16, .025]} radius={.045} color={accent} emissive={accent} intensity={.4} />
      {[.1, -.02, -.13].map((y, row) => <SoftBox key={row} size={[row === 2 ? .24 : .39, .025, .014]} position={[0, y, .027]} color={row === 0 ? accent : '#55717e'} radius={.007} />)}
    </group>)}
    {[-.99, .99].map(x => <SoftBox key={x} size={[.07, .72, .08]} position={[x, .3, -.035]} color="#4f646f" radius={.02} />)}
  </group>
}

function WorkloadTracks({ accent, active, reducedMotion }: { accent: string; active: boolean; reducedMotion: boolean }) {
  const ref = useRef<THREE.Group>(null)
  useFrame(({ clock }) => {
    if (!ref.current || reducedMotion) return
    ref.current.children.forEach((child, i) => { child.position.x = active ? ((clock.elapsedTime * .28 + i * .37) % 1.8) - .9 : -.58 + i * .39 })
  })
  return <group position={[0, 1.33, -1.6]}>
    <SoftBox size={[2.55, 1.08, .13]} color="#40535e" radius={.075} />
    <SoftBox size={[2.32, .86, .025]} position={[0, 0, .083]} color="#152c32" radius={.035} />
    {[-.23, 0, .23].map((y, i) => <SoftBox key={i} size={[1.94, .025, .018]} position={[0, y, .106]} color="#3b5960" radius={.006} />)}
    <group ref={ref}>
      {Array.from({ length: 5 }, (_, i) => <group key={i} position={[-.58 + i * .39, (i % 3 - 1) * .23, .135]}>
        <SoftBox size={[.18, .10, .04]} color={i === 3 ? '#d3b081' : accent} radius={.025} emissive={accent} intensity={.25} />
      </group>)}
    </group>
    {[-1.02, 1.02].map(x => <SoftBox key={x} size={[.08, 1.06, .09]} position={[x, -.77, -.045]} color="#4f626a" radius={.025} />)}
  </group>
}

function Shield({ color, scale = 1 }: { color: string; scale?: number }) {
  const geometry = useMemo(() => {
    const shape = new THREE.Shape()
    shape.moveTo(-.24, .24); shape.quadraticCurveTo(0, .34, .24, .24); shape.lineTo(.21, -.08)
    shape.quadraticCurveTo(.18, -.2, 0, -.31); shape.quadraticCurveTo(-.18, -.2, -.21, -.08); shape.closePath()
    return new THREE.ExtrudeGeometry(shape, { depth: .035, bevelEnabled: true, bevelSegments: 2, steps: 1, bevelSize: .022, bevelThickness: .018 })
  }, [])
  return <group scale={scale}>
    <mesh geometry={geometry} castShadow><meshStandardMaterial color={color} roughness={.47} metalness={.22} /></mesh>
    <mesh position={[0, .035, .063]} rotation={[0, 0, -.7]}><boxGeometry args={[.065, .15, .013]} /><meshStandardMaterial color="#ecede4" /></mesh>
    <mesh position={[.068, .085, .063]} rotation={[0, 0, .65]}><boxGeometry args={[.061, .26, .013]} /><meshStandardMaterial color="#ecede4" /></mesh>
  </group>
}

function Accessory({ role, color }: { role: Role; color: string }) {
  if (role === 'custom') return <group position={[0, -.28, .18]} rotation={[.08, .2, -.12]}>
    <SoftBox size={[.31, .4, .07]} color="#405b6c" radius={.04} />
    <SoftBox size={[.255, .325, .013]} position={[0, .015, .043]} color="#193440" radius={.023} />
    <SoftBox size={[.025, .21, .012]} position={[-.062, .015, .054]} color={color} emissive={color} intensity={.35} radius={.007} />
    {[.084, .024, -.036].map((y, i) => <SoftBox key={y} size={[.09 - i * .012, .021, .012]} position={[.033, y, .055]} color={i===0?'#d7e9e8':color} emissive={color} intensity={.15} radius={.006} />)}
    <Ball position={[0, -.155, .049]} radius={.016} color={color} />
  </group>
  if (role === 'hr') return <group position={[0, -.27, .17]} rotation={[.18, .23, -.15]}>
    <SoftBox size={[.29, .39, .10]} color={color} radius={.035} />
    <SoftBox size={[.24, .32, .084]} position={[.017, 0, -.008]} color="#e1e8df" radius={.017} />
    <SoftBox size={[.27, .37, .018]} position={[0, 0, .06]} color={color} radius={.02} />
    <SoftBox size={[.13, .026, .008]} position={[0, .09, .073]} color="#e5eee9" radius={.005} />
    <SoftBox size={[.10, .017, .008]} position={[0, .035, .073]} color="#b1dfd3" radius={.005} />
  </group>
  if (role === 'finance') return <group position={[0, -.3, .17]} rotation={[.08, .18, -.13]}>
    <SoftBox size={[.29, .4, .085]} color={color} radius={.035} />
    <SoftBox size={[.2, .077, .015]} position={[0, .11, .05]} color="#263841" radius={.015} />
    {Array.from({ length: 9 }, (_, i) => <SoftBox key={i} size={[.047, .043, .015]} position={[(i % 3 - 1) * .075, .017 - Math.floor(i / 3) * .069, .057]} color={i === 8 ? '#d9e1dd' : '#cabfec'} radius={.009} />)}
  </group>
  if (role === 'security') return <group position={[0, -.22, .17]} rotation={[0, .15, -.15]}><Shield color={color} scale={.74} /></group>
  if (role === 'optimizer') return <group position={[0, -.29, .18]} rotation={[0, .22, -.08]}>
    <SoftBox size={[.29, .29, .07]} color="#35594f" radius={.035} />
    <SoftBox size={[.18, .18, .018]} position={[0, 0, .052]} color={color} emissive={color} intensity={.6} radius={.018} />
    {[-1, 1].map(side => [0, 1, 2].map(i => <SoftBox key={`${side}-${i}`} size={[.035, .021, .029]} position={[side * .158, -.07 + i * .07, 0]} color="#b9c9bd" radius={.005} />))}
  </group>
  return null
}

function Mascot({ role, color, status, reducedMotion, seed = 0, atDesk = false, heavy = false, greeting = false, walking = false, lastActivityAt }: {
  role: Role; color: string; status: string; reducedMotion: boolean; seed?: number; atDesk?: boolean; heavy?: boolean; greeting?: boolean; walking?: boolean; lastActivityAt?: string | null
}) {
  const root = useRef<THREE.Group>(null), torso = useRef<THREE.Group>(null), head = useRef<THREE.Group>(null), eyes = useRef<THREE.Group>(null), mouth = useRef<THREE.Mesh>(null)
  const left = useRef<THREE.Group>(null), right = useRef<THREE.Group>(null), leftElbow = useRef<THREE.Group>(null), rightElbow = useRef<THREE.Group>(null)
  const leftLeg = useRef<THREE.Group>(null), rightLeg = useRef<THREE.Group>(null), leftShin = useRef<THREE.Group>(null), rightShin = useRef<THREE.Group>(null)
  const previousStatus = useRef(status), transitionAt = useRef<number | null>(null)
  const working = status === 'running' && atDesk && !walking && !greeting
  useEffect(() => {
    // An old saved completed state never celebrates merely because it mounts.
    if (status === 'completed' && ['running', 'queued'].includes(previousStatus.current)) transitionAt.current = Date.now()
    previousStatus.current = status
  }, [status])
  useFrame(({ clock }, delta) => {
    if (!root.current || !head.current || !left.current || !right.current || !torso.current) return
    const t = clock.elapsedTime + (seed % 29) * .37
    const stamp = lastActivityAt ? Date.parse(lastActivityAt) : transitionAt.current
    const age = stamp === null || !Number.isFinite(stamp) ? Infinity : (Date.now() - stamp) / 1000
    const celebrating = !reducedMotion && status === 'completed' && age >= 0 && age < 2.4 && !walking && !greeting
    const damp = (current: number, target: number) => reducedMotion ? target : THREE.MathUtils.damp(current, target, 7, delta)
    root.current.position.y = .17 + (reducedMotion ? 0 : walking ? Math.abs(Math.sin(t * 8)) * .035 : Math.sin(t * 1.65) * .009) + (!reducedMotion && celebrating ? Math.max(0, Math.sin(age * 8)) * .1 : 0)
    root.current.rotation.z = reducedMotion ? 0 : walking ? Math.sin(t * 8) * .025 : Math.sin(t * 1.4) * .008
    root.current.rotation.y = damp(root.current.rotation.y, working ? Math.PI + .08 : atDesk && !walking ? .12 : 0)
    torso.current.position.y = damp(torso.current.position.y, working ? -.115 : 0)
    torso.current.rotation.x = damp(torso.current.rotation.x, working ? .055 : 0)
    head.current.rotation.y = damp(head.current.rotation.y, greeting ? -.2 : reducedMotion ? .04 : working ? Math.sin(t * .85) * .055 : Math.sin(t * .38) * .18)
    head.current.rotation.x = damp(head.current.rotation.x, working ? .14 + (reducedMotion ? 0 : Math.sin(t * 3) * .018) : status === 'paused' ? -.045 : greeting && !reducedMotion ? Math.sin(t * 2.6) * .065 : 0)
    const idleStretch = !reducedMotion && !working && !walking && !greeting && (t + seed) % 17 > 15.7
    left.current.rotation.x = damp(left.current.rotation.x, walking ? Math.sin(t * 8) * .38 : working ? -1.02 + (reducedMotion ? 0 : Math.sin(t * 9.4) * .045) : -.1)
    right.current.rotation.x = damp(right.current.rotation.x, walking ? -Math.sin(t * 8) * .38 : working ? -1.02 + (reducedMotion ? 0 : Math.sin(t * 9.4 + 1.5) * .045) : greeting ? -.7 : idleStretch ? -.32 : -.1)
    right.current.rotation.z = damp(right.current.rotation.z, greeting || celebrating ? -.82 + (reducedMotion ? 0 : Math.sin(t * 4.1) * .09) : idleStretch ? -.55 : working ? -.07 : -.12)
    left.current.rotation.z = damp(left.current.rotation.z, celebrating ? .3 : working ? .07 : .12)
    if (leftElbow.current) leftElbow.current.rotation.x = damp(leftElbow.current.rotation.x, working ? -.63 + (reducedMotion ? 0 : Math.sin(t * 12) * .08) : -.06)
    if (rightElbow.current) rightElbow.current.rotation.x = damp(rightElbow.current.rotation.x, working ? -.63 + (reducedMotion ? 0 : Math.sin(t * 12 + 2) * .08) : greeting ? -.7 : -.06)
    for (const [leg, shin, side] of [[leftLeg.current, leftShin.current, 1], [rightLeg.current, rightShin.current, -1]] as const) {
      if (leg) { leg.position.y = damp(leg.position.y, working ? .405 : .52); leg.rotation.x = damp(leg.rotation.x, working ? -1.05 : walking && !reducedMotion ? Math.sin(t * 8) * .43 * side : 0) }
      if (shin) shin.rotation.x = damp(shin.rotation.x, working ? 1.05 : 0)
    }
    if (eyes.current) { const phase = (t + seed * .13) % 6.1; eyes.current.scale.y = reducedMotion ? 1 : phase > 5.91 ? .2 + Math.abs(phase - 6.005) * 8 : 1 }
    if (mouth.current) mouth.current.scale.y = !reducedMotion && greeting ? 1 + Math.sin(t * 7) * .2 : 1
  })
  const alert = ['error', 'blocked', 'security_blocked'].includes(status)
  const indicator = heavy ? '#e58978' : alert || status === 'queued' ? '#e2b779' : status === 'completed' ? '#83c5a7' : status === 'paused' ? '#8395a4' : color
  const skin = new THREE.Color(WHITE).lerp(new THREE.Color(heavy ? '#efa08d' : '#efcda6'), heavy ? .32 : status === 'running' ? .05 : 0).getStyle()
  const glow = heavy ? '#e66650' : '#000000'
  return <group ref={root} position={[0, .17, 0]}>
    {([-1, 1] as const).map(side => <group key={side} ref={side === -1 ? leftLeg : rightLeg} position={[side * .2, .52, 0]}>
      <mesh position={[0, -.11, 0]} castShadow><capsuleGeometry args={[.135, .15, 4, 10]} /><meshStandardMaterial color={skin} roughness={.65} /></mesh>
      <Ball position={[0, -.23, 0]} radius={.135} color={skin} />
      <group ref={side === -1 ? leftShin : rightShin} position={[0, -.23, 0]}>
        <mesh position={[0, -.115, 0]} castShadow><capsuleGeometry args={[.12, .13, 4, 10]} /><meshStandardMaterial color={skin} roughness={.65} /></mesh>
        <Ball position={[0, -.30, .1]} radius={.17} color={skin} scale={[.9, .6, 1.4]} />
      </group>
    </group>)}
    <group ref={torso}>
      <Ball position={[0, .77, 0]} radius={.43} scale={[1, 1.18, .92]} color={skin} emissive={glow} intensity={heavy ? .24 : 0} />
      <SoftBox size={[.29, .08, .11]} position={[0, 1.05, .33]} color={color} emissive={indicator} intensity={heavy ? .7 : .08} radius={.03} />
      <Ball position={[0, 1.09, .37]} radius={.035} color="#dcece7" />
      <group ref={head} position={[0, 1.56, 0]}>
        <Ball position={[0, 0, 0]} radius={.55} scale={[1.04, .96, 1]} color={skin} emissive={glow} intensity={heavy ? .16 : 0} />
        {[-1, 1].map(side => <Ball key={side} position={[side * .56, -.04, 0]} radius={.105} color={skin} scale={[.7, 1, .82]} />)}
        <group ref={eyes} position={[0, .035, .523]}>{[-1, 1].map(side => <Ball key={side} position={[side * .165, 0, 0]} radius={.045} color="#17232c" scale={[.92, 1.12, .42]} />)}</group>
        {[-1, 1].map(side => <Ball key={side} position={[side * .22, -.087, .499]} radius={.048} color="#cfdbd7" scale={[1, .46, .15]} />)}
        <mesh ref={mouth} position={[0, -.115, .526]} rotation={[0, 0, Math.PI]}><torusGeometry args={[alert ? .09 : .115, .012, 5, 18, Math.PI]} /><meshStandardMaterial color="#26343b" roughness={.8} /></mesh>
        <mesh position={[.016, .519, -.05]} rotation={[.18, 0, -.2 + (seed % 7 - 3) * .08]} castShadow><capsuleGeometry args={[.063, .13, 4, 10]} /><meshStandardMaterial color={skin} roughness={.7} /></mesh>
        {role === 'support' && <group>
          <mesh position={[0, -.02, 0]}><torusGeometry args={[.583, .031, 6, 28, Math.PI]} /><meshStandardMaterial color="#3a5160" roughness={.5} /></mesh>
          {[-1, 1].map(side => <SoftBox key={side} size={[.105, .23, .21]} position={[side * .59, -.045, 0]} color="#3a5160" radius={.04} />)}
          <Cable points={[[.59, -.11, .08], [.57, -.22, .29], [.3, -.24, .51]]} color="#3c5360" radius={.025} />
          <Ball position={[.3, -.24, .51]} radius={.044} color={color} />
        </group>}
      </group>
      {([-1, 1] as const).map(side => <group key={side} ref={side === -1 ? left : right} position={[side * .445, 1.04, 0]} rotation={[0, 0, -side * .12]}>
        <mesh position={[0, -.13, 0]} castShadow><capsuleGeometry args={[.12, .16, 4, 10]} /><meshStandardMaterial color={skin} roughness={.64} /></mesh>
        <Ball position={[0, -.28, 0]} radius={.12} color={skin} />
        <group ref={side === -1 ? leftElbow : rightElbow} position={[0, -.28, 0]}>
          <mesh position={[0, -.11, 0]} castShadow><capsuleGeometry args={[.11, .13, 4, 10]} /><meshStandardMaterial color={skin} roughness={.64} /></mesh>
          <Ball position={[0, -.245, .015]} radius={.13} color={skin} />
          {side === -1 && !working && <Accessory role={role} color={color} />}
        </group>
      </group>)}
    </group>
    <group position={[.72, 2.13, .02]}>
      <Ball position={[0, 0, 0]} radius={.074} color={indicator} emissive={indicator} intensity={heavy ? .95 : .45} />
      {(alert || status === 'queued') && <mesh rotation={[0, 0, .15]}><torusGeometry args={[.12, .011, 5, 20]} /><meshStandardMaterial color={indicator} /></mesh>}
    </group>
  </group>
}

function AgentNameTag({ agent, role, position, accent, selected, compact, labelScale = 1, workload, workState, interactionLabel, onSelect, onHover }: {
  agent?: WorldAgent; role: Role; position: Point; accent: string; selected: boolean; compact: boolean; labelScale?: number; workload?: WorldWorkload; workState?: 'working' | 'heavy workload'; interactionLabel?: string
  onSelect: (id: string) => void; onHover: (id: string | null) => void
}) {
  const name = agent?.name || (agent ? `${ROLE_NAME[role]} agent` : `${ROLE_NAME[role]} station`)
  return <Html position={position} center style={{ pointerEvents: 'auto', whiteSpace: 'nowrap' }}>
    <button type="button" disabled={!agent} aria-pressed={selected} aria-label={agent ? `Open ${name}, ${ROLE_NAME[role]} agent ${agent.id}, ${workState || agent.status}${workState === 'heavy workload' ? ', workload visualization, not measured GPU temperature' : ''}${interactionLabel ? `, ${interactionLabel}` : ''}` : name} title={agent ? `${name} · ${ROLE_NAME[role]} · ${agent.id}${workState ? ` · ${workState}` : ''}${workState === 'heavy workload' ? ' (not measured GPU temperature)' : ''}${interactionLabel ? ` · ${interactionLabel}` : ''}` : name}
      onClick={() => agent && onSelect(agent.id)} onMouseEnter={() => agent && onHover(agent.id)} onMouseLeave={() => onHover(null)} onFocus={() => agent && onHover(agent.id)} onBlur={() => onHover(null)}
      style={{ padding: compact ? '5px 7px' : '5px 9px', border: `1px solid ${selected ? accent : '#69828b33'}`, borderRadius: 6, color: '#ecf2f2', background: selected ? '#243b42e8' : '#13202be8', cursor: agent ? 'pointer' : 'default', fontFamily: 'inherit', textAlign: 'left', boxShadow: '0 5px 20px #0003', minWidth: compact ? 60 : 88, maxWidth: compact ? 100 : 140, transform: `scale(${labelScale})`, transformOrigin: 'center' }}>
      <span style={{ display: 'flex', alignItems: 'center', gap: compact ? 4 : 6, fontSize: compact ? 9 : 10, fontWeight: 650, letterSpacing: '.025em' }}>
        <span style={{ width: 5, height: 5, flexShrink: 0, background: accent, borderRadius: '50%', display: 'inline-block', boxShadow: agent?.status === 'running' ? `0 0 7px ${accent}` : 'none' }} />
        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{name}</span>
        {!compact && <span style={{ marginLeft: 'auto', fontSize: 10, opacity: .4 }}>↗</span>}
      </span>
      <span style={{ display: 'block', marginTop: 3, fontSize: compact ? 6 : 7, color: workState === 'heavy workload' ? '#e7ae9e' : '#8b9da8', letterSpacing: '.07em', textTransform: 'uppercase' }}>{ROLE_NAME[role]}{agent?.tagId ? ` · ${agent.tagId}` : ''}{agent ? ` · ${workState || agent.status.replaceAll('_', ' ')}` : ' · unoccupied'}{workload?.queued_jobs ? ` · ${workload.queued_jobs} queued` : ''}</span>
      {interactionLabel && <span style={{display:'block',marginTop:4,fontSize:7,color:'#b9dbcc',whiteSpace:'normal'}}>{interactionLabel}</span>}
    </button>
  </Html>
}

const DEFAULT_CATEGORIES: WorldCategory[] = [...ZONES.map(zone => ({id:zone.role,name:zone.label,color:zone.color})), {id:'custom',name:'Custom',color:'#94bdd0'}]
type CategoryZone = {category:WorldCategory;agents:WorldAgent[];position:Point;width:number;depth:number;columns:number}
type AgentLocation = {position:Point;color:string;category:WorldCategory}
function categoryLayout(agents:WorldAgent[],categories?:WorldCategory[]) {
  const known = [...(categories?.length ? categories : DEFAULT_CATEGORIES)]
  for (const agent of agents) { const id=agent.category_id || agentRole(agent); if(!known.some(category=>category.id===id)) known.push({id,name:`Category ${id.slice(-4)}`,color:'#94bdd0'}) }
  const zones = known.map(category => {
    const members=agents.filter(agent=>(agent.category_id||agentRole(agent))===category.id)
    const columns=Math.min(Math.max(1,members.length),6,Math.max(1,Math.ceil(Math.sqrt(members.length*2))))
    return {category,agents:members,position:[0,0,0] as Point,width:members.length ? columns*3.2+.7 : 3.1,depth:members.length ? Math.ceil(members.length/columns)*3.7+1.0 : 1.8,columns}
  })
  const rows:CategoryZone[][]=[]
  let row:CategoryZone[]=[],width=0
  // Small categories form a balanced room rather than one distant, very wide shelf.
  const compactRoom=zones.length>=4&&zones.length<=9&&zones.every(zone=>zone.agents.length<=2)
  for(const zone of zones){if(row.length&&(width+1.15+zone.width>28||(compactRoom&&row.length>=3))){rows.push(row);row=[];width=0}row.push(zone);width+=zone.width+(row.length>1?1.15:0)}
  if(row.length)rows.push(row)
  let z=0,roomWidth=17,hubZ=0
  for(let index=0;index<rows.length;index++){
    const members=rows[index],rowWidth=members.reduce((sum,zone)=>sum+zone.width,0)+(members.length-1)*1.15,rowDepth=Math.max(...members.map(zone=>zone.depth))
    roomWidth=Math.max(roomWidth,rowWidth+2.0)
    let x=-rowWidth/2
    for(const zone of members){zone.position=[x+zone.width/2,0,z+zone.depth/2];x+=zone.width+1.15}
    z+=rowDepth
    if(index===0){hubZ=z+2.2;z+=4.4}else if(index<rows.length-1)z+=1.4
  }
  const roomDepth=Math.max(11,z+1.2),locations=new Map<string,AgentLocation>()
  for(const zone of zones)zone.agents.forEach((agent,index)=>{
    const cols=Math.min(zone.columns,zone.agents.length),col=index%cols,line=Math.floor(index/cols)
    locations.set(agent.id,{position:[zone.position[0]+(col-(cols-1)/2)*3.2,.15,zone.position[2]-zone.depth/2+2.0+line*3.7],color:agentColor(agent,zone.category.color),category:zone.category})
  })
  return {zones,locations,roomWidth,roomDepth,hubPosition:[0,.04,hubZ] as Point}
}

function useWorkPressure(agent:WorldAgent,workload:WorldWorkload={}) {
  const [,tick]=useState(0)
  const working=agent.status==='running'||(workload.running_jobs??0)>0
  const start=workload.running_since?Date.parse(workload.running_since):NaN
  const elapsed=Number.isFinite(start)?Math.max(0,(Date.now()-start)/1000):0
  useEffect(()=>{
    if(!working||!Number.isFinite(start)||elapsed>=20)return
    const timer=setTimeout(()=>tick(value=>value+1),Math.max(1,(20-elapsed)*1000))
    return()=>clearTimeout(timer)
  },[working,start])
  return {working,heavy:working&&((workload.queued_jobs??0)>=2||elapsed>=20)}
}

function Chair({color}:{color:string}) {
  return <group position={[0,0,.38]}>
    <mesh position={[0,.26,0]} castShadow><cylinderGeometry args={[.07,.1,.4,12]}/><meshStandardMaterial color="#4b5d66" metalness={.4} roughness={.45}/></mesh>
    <SoftBox size={[.79,.14,.73]} position={[0,.55,0]} color="#405665" radius={.07}/>
    <SoftBox size={[.74,.12,.65]} position={[0,.64,-.015]} color="#526f7b" radius={.055}/>
    <SoftBox size={[.77,.68,.14]} position={[0,.93,.31]} color="#405665" radius={.07}/>
    <SoftBox size={[.64,.56,.07]} position={[0,.94,.225]} color={color} radius={.04}/>
    {[-1,1].map(side=><SoftBox key={side} size={[.11,.07,.57]} position={[side*.46,.85,-.045]} color="#68818c" radius={.025}/>)}
    {Array.from({length:5},(_,i)=>{const a=i*Math.PI*2/5;return <group key={i} rotation={[0,a,0]}><SoftBox size={[.07,.055,.53]} position={[0,.085,.22]} color="#526a76" radius={.025}/><Ball position={[0,.075,.46]} radius={.07} color="#182a35"/></group>})}
  </group>
}

function WorkSmoke({seed}:{seed:number}) {
  const clouds=useRef<THREE.Group>(null)
  useFrame(({clock})=>{clouds.current?.children.forEach((object,index)=>{const mesh=object as THREE.Mesh<THREE.SphereGeometry,THREE.MeshBasicMaterial>,u=(clock.elapsedTime*.36+index*.23+(seed%9)*.1)%1;mesh.position.set(.62+Math.sin(u*5+index)*.12,2.15+u*1.15,-.06+Math.cos(u*4+index)*.08);mesh.scale.setScalar(.10+u*.18);mesh.material.opacity=Math.sin(u*Math.PI)*.13})})
  return <group ref={clouds}>{Array.from({length:4},(_,i)=><mesh key={i} position={[.62,2.4+i*.1,0]}><sphereGeometry args={[1,10,8]}/><meshBasicMaterial color="#bdc6c7" transparent opacity={.08} depthWrite={false}/></mesh>)}</group>
}

const REPLAY_SECONDS=25
function interactionPhase(interaction?:WorldInteraction) {
  if(!interaction)return {active:false,walking:false,greeting:false,travel:0}
  const end=interaction.completed_at?Date.parse(interaction.completed_at):NaN
  if(interaction.status!=='completed'||!Number.isFinite(end))return {active:false,walking:false,greeting:false,travel:0}
  const age=(Date.now()-end)/1000
  if(age<0||age>=REPLAY_SECONDS)return {active:false,walking:false,greeting:false,travel:0}
  const p=age/REPLAY_SECONDS
  return {active:true,walking:p<.28||p>.65,greeting:p>=.28&&p<=.65,travel:p<.28?p/.28:p>.65?1-(p-.65)/.35:1}
}

function AgentActor({agent,location,destination,interaction,recipientInteraction,workload,selected,hovered,reducedMotion,labelScale,onSelect,onHover}:{
  agent:WorldAgent;location:AgentLocation;destination?:AgentLocation;interaction?:WorldInteraction;recipientInteraction?:WorldInteraction;workload?:WorldWorkload;selected:boolean;hovered:boolean;reducedMotion:boolean;labelScale:number;onSelect:(id:string)=>void;onHover:(id:string|null)=>void
}) {
  const actor=useRef<THREE.Group>(null),prior=useRef('')
  const [pose,setPose]=useState({walking:false,greeting:false,recorded:false})
  const {working,heavy}=useWorkPressure(agent,workload)
  const path=useMemo(()=>destination?new THREE.CatmullRomCurve3([
    new THREE.Vector3(0,0,.63),new THREE.Vector3(0,0,1.25),new THREE.Vector3((destination.position[0]-location.position[0])*.5,0,Math.max(1.25,destination.position[2]-location.position[2]+1.3)),new THREE.Vector3(destination.position[0]-location.position[0]-1.0,0,destination.position[2]-location.position[2]+.8)
  ]):null,[destination,location])
  useFrame((_,delta)=>{
    if(!actor.current)return
    const visit=interactionPhase(interaction),received=interactionPhase(recipientInteraction)
    const walking=!!path&&visit.walking&&!reducedMotion,greeting=(visit.greeting||received.greeting)&&!reducedMotion
    const signature=`${walking}:${greeting}:${visit.active||received.active}`
    if(signature!==prior.current){prior.current=signature;setPose({walking,greeting,recorded:visit.active||received.active})}
    if(path&&visit.active&&!reducedMotion){const point=path.getPoint(THREE.MathUtils.clamp(visit.travel,0,1));actor.current.position.copy(point);const tangent=path.getTangent(THREE.MathUtils.clamp(visit.travel,0,1));actor.current.rotation.y=visit.walking?Math.atan2(tangent.x,tangent.z)+(visit.travel===1?0:visit.travel>0&&((Date.now()-Date.parse(interaction!.completed_at!))/1000)>REPLAY_SECONDS*.65?Math.PI:0):Math.atan2(destination!.position[0]-location.position[0]-point.x,destination!.position[2]-location.position[2]-point.z)}
    else{actor.current.position.x=reducedMotion?0:THREE.MathUtils.damp(actor.current.position.x,0,8,delta);actor.current.position.z=reducedMotion?(working ? .35 : .63):THREE.MathUtils.damp(actor.current.position.z,working ? .35 : .63,6,delta);actor.current.rotation.y=reducedMotion?0:THREE.MathUtils.damp(actor.current.rotation.y,0,8,delta)}
  })
  useEffect(()=>{
    // A hidden canvas may miss the expiry frame. Reset the frame guard as well as
    // its React pose so a later real review always restores its label and limbs.
    prior.current=''
    const visit=interactionPhase(interaction),received=interactionPhase(recipientInteraction)
    setPose({walking:!!path&&visit.walking&&!reducedMotion,greeting:(visit.greeting||received.greeting)&&!reducedMotion,recorded:visit.active||received.active})
    const ends=[interaction,recipientInteraction].flatMap(record=>record?.completed_at&&record.status==='completed'?[Date.parse(record.completed_at)]:[]).filter(Number.isFinite)
    if(!ends.length)return
    const remaining=REPLAY_SECONDS*1000-(Date.now()-Math.max(...ends))
    if(remaining<=0)return
    const timer=setTimeout(()=>{prior.current='';setPose({walking:false,greeting:false,recorded:false})},remaining)
    return()=>clearTimeout(timer)
  },[interaction?.id,interaction?.completed_at,interaction?.status,recipientInteraction?.id,recipientInteraction?.completed_at,recipientInteraction?.status,reducedMotion,!!path])
  const status=working?'running':agent.status
  return <group ref={actor} position={[0,0,.63]} onClick={(event:ThreeEvent<MouseEvent>)=>{event.stopPropagation();onSelect(agent.id)}} onPointerOver={event=>{event.stopPropagation();onHover(agent.id)}} onPointerOut={()=>onHover(null)}>
    <Mascot role={agentRole(agent)} color={location.color} status={status} reducedMotion={reducedMotion} seed={agentSeed(agent.id)} atDesk heavy={heavy} walking={pose.walking} greeting={pose.greeting} lastActivityAt={agent.last_activity_at}/>
    {heavy&&!reducedMotion&&<WorkSmoke seed={agentSeed(agent.id)}/>}
    <AgentNameTag agent={agent} role={agentRole(agent)} position={[0,.18,1.15]} accent={heavy?'#e58978':location.color} selected={selected} compact labelScale={hovered||selected?1:labelScale} workload={workload} workState={heavy?'heavy workload':working?'working':undefined} interactionLabel={pose.recorded?'Finance review completed · recorded':undefined} onSelect={onSelect} onHover={onHover}/>
  </group>
}

function CategoryIsland({zone,locations,selected,hovered,workloads,interactions,reducedMotion,labelScale,onSelect,onHover}:{
  zone:CategoryZone;locations:Map<string,AgentLocation>;selected:string|null;hovered:string|null;workloads:Record<string,WorldWorkload>;interactions:WorldInteraction[];reducedMotion:boolean;labelScale:number;onSelect:(id:string)=>void;onHover:(id:string|null)=>void
}) {
  return <group>
    <group position={zone.position}>
      <SoftBox size={[zone.width,.18,zone.depth]} position={[0,.025,0]} color="#283945" radius={.16}/>
      <SoftBox size={[zone.width-.22,.024,zone.depth-.22]} position={[0,.13,0]} color="#30434d" radius={.12}/>
      <SoftBox size={[zone.width-.45,.018,.035]} position={[0,.155,-zone.depth/2+.25]} color={zone.category.color} emissive={zone.category.color} intensity={.35} radius={.009}/>
      <Html position={[0,.25,zone.depth/2+.25]} center style={{pointerEvents:'none'}}><div style={{background:'#142630ed',border:`1px solid ${zone.category.color}66`,borderRadius:7,padding:'5px 10px',fontFamily:'inherit',textAlign:'center',width:'max-content',minWidth:90,maxWidth:180,color:'#d5e9ea',boxShadow:'0 4px 14px #0003'}}><strong style={{display:'block',fontSize:10,fontWeight:600,letterSpacing:'.04em',whiteSpace:'normal',overflowWrap:'break-word'}}>{zone.category.name}</strong><span style={{display:'block',fontSize:7,color:zone.category.color,marginTop:2}}>{zone.agents.length} {zone.agents.length===1?'agent':'agents'}</span></div></Html>
      {!zone.agents.length&&<Plant position={[0,.15,.15]} size={.48}/>}
    </group>
    {zone.agents.map(agent=>{
      const location=locations.get(agent.id)!,visit=interactions.find(item=>item.from_agent_id===agent.id),received=interactions.find(item=>item.to_agent_id===agent.id),destination=visit?locations.get(visit.to_agent_id):undefined
      return <group key={agent.id} position={location.position}>
        <SoftBox size={[2.98,.018,3.42]} position={[0,.009,0]} color={selected===agent.id?'#3d5660':hovered===agent.id?'#36505c':'#2c414b'} radius={.1}/>
        <Desk accent={location.color} role={agentRole(agent)}/><Chair color={location.color}/>
        <SoftBox size={[2.76,.015,.027]} position={[0,.034,1.62]} color={location.color} emissive={location.color} intensity={selected===agent.id ? .7 : .18} radius={.006}/>
        <AgentActor agent={agent} location={location} destination={destination} interaction={visit} recipientInteraction={received} workload={workloads[agent.id]} selected={selected===agent.id} hovered={hovered===agent.id} reducedMotion={reducedMotion} labelScale={labelScale} onSelect={onSelect} onHover={onHover}/>
        {agentSeed(agent.id)%4===0&&<Plant position={[-1.25,0,-1.0]} size={.46}/>}
      </group>
    })}
  </group>
}

function RecordedReview({interaction,from,to,reducedMotion}:{interaction:WorldInteraction;from:AgentLocation;to:AgentLocation;reducedMotion:boolean}) {
  const [visible,setVisible]=useState(()=>interactionPhase(interaction).active)
  useEffect(()=>{setVisible(interactionPhase(interaction).active);const end=interaction.completed_at?Date.parse(interaction.completed_at):NaN;if(!Number.isFinite(end))return;const timer=setTimeout(()=>setVisible(false),Math.max(1,REPLAY_SECONDS*1000-(Date.now()-end)));return()=>clearTimeout(timer)},[interaction.id,interaction.completed_at])
  const points=useMemo<Point[]>(()=>[[from.position[0],.19,from.position[2]+1.3],[(from.position[0]+to.position[0])/2,.23,Math.max(from.position[2],to.position[2])+1.5],[to.position[0]-1,.19,to.position[2]+.8]],[from,to])
  if(!visible)return null
  return <group><Cable points={points} color="#a5d4c0" radius={reducedMotion ? .012 : .019} emissive/></group>
}

function OperationsHub({ activeCount, reducedMotion, position = [-.15, .04, 1.28] }: { activeCount: number; reducedMotion: boolean; position?:Point }) {
  const ring = useRef<THREE.Group>(null)
  useFrame(({ clock }) => { if (ring.current && !reducedMotion) ring.current.rotation.y = clock.elapsedTime * .065 })
  return <group position={position}>
    <mesh position={[0, .07, 0]} castShadow receiveShadow><cylinderGeometry args={[1.78, 1.88, .19, 64]} /><meshStandardMaterial color="#2c3e48" roughness={.45} metalness={.35} /></mesh>
    <mesh position={[0, .172, 0]}><cylinderGeometry args={[1.55, 1.55, .026, 64]} /><meshStandardMaterial color="#304c54" roughness={.34} metalness={.27} /></mesh>
    {[1.72, 1.45].map((radius, i) => <mesh key={radius} position={[0, .184, 0]} rotation={[-Math.PI / 2, 0, 0]}><torusGeometry args={[radius, i === 0 ? .018 : .009, 6, 64]} /><meshStandardMaterial color="#68c6c2" emissive="#68c6c2" emissiveIntensity={i === 0 ? .65 : .2} /></mesh>)}
    <mesh position={[0, .31, 0]} castShadow><cylinderGeometry args={[.91, 1.08, .27, 6]} /><meshStandardMaterial color="#435b65" roughness={.36} metalness={.35} /></mesh>
    <mesh position={[0, .51, 0]} castShadow><cylinderGeometry args={[.79, .90, .15, 6]} /><meshStandardMaterial color="#688b95" roughness={.25} metalness={.25} /></mesh>
    <mesh position={[0, .61, 0]}><cylinderGeometry args={[.71, .71, .06, 6]} /><meshStandardMaterial color="#69bfc1" emissive="#6dc8c8" emissiveIntensity={.4} roughness={.26} /></mesh>
    <group ref={ring} position={[0, 1.05, 0]}>
      <mesh rotation={[-Math.PI / 2, 0, 0]}><torusGeometry args={[.67, .025, 8, 64]} /><meshStandardMaterial color="#a6d2d0" emissive="#47a9ad" emissiveIntensity={.3} metalness={.3} roughness={.25} /></mesh>
      {Array.from({ length: 5 }, (_, i) => <Ball key={i} position={[Math.cos(i * Math.PI * 2 / 5) * .67, 0, Math.sin(i * Math.PI * 2 / 5) * .67]} radius={.065} color={i < activeCount ? '#a5a0df' : '#88c9c4'} emissive={i < activeCount ? '#a5a0df' : '#88c9c4'} intensity={.65} />)}
      <mesh position={[0, -.16, 0]} rotation={[.1, .4, -.07]} castShadow><octahedronGeometry args={[.26]} /><meshStandardMaterial color="#a5dcd6" emissive="#6ac8c3" emissiveIntensity={.25} metalness={.3} roughness={.23} /></mesh>
    </group>
    {[-.63, .63].map(x => <SoftBox key={x} size={[.026, .45, .026]} position={[x, .81, 0]} color="#7aabae" radius={.006} />)}
    <pointLight position={[0, .83, 0]} intensity={2.2} color="#79d0cc" distance={4.3} decay={2} />
    <Html position={[0, .26, 2.03]} center style={{ pointerEvents: 'none' }}>
      <div style={{ textAlign: 'center', whiteSpace: 'nowrap', fontFamily: 'inherit', color: '#9db4bd' }}>
        <div style={{ fontSize: 9, fontWeight: 600, letterSpacing: '.24em' }}>OPERATIONS HUB</div>
        <div style={{ fontSize: 7, color: '#5e848c', marginTop: 5, letterSpacing: '.13em' }}>PRIVATE · LOCAL · CONNECTED</div>
      </div>
    </Html>
  </group>
}

function Architecture({width,depth}:{width:number;depth:number}) {
  return <group>
    <SoftBox size={[width,.43,depth]} position={[0,-.28,depth/2-.5]} color="#16252f" radius={.22}/>
    <SoftBox size={[width-.25,.045,depth-.25]} position={[0,-.035,depth/2-.5]} color="#1c2d37" radius={.18}/>
    <SoftBox size={[width-.6,.024,.032]} position={[0,-.15,depth-.54]} color="#608e95" emissive="#527e88" intensity={.3} radius={.008}/>
    {[-1,1].map(side=><SoftBox key={side} size={[.022,.025,depth-.65]} position={[side*(width/2-.22),-.15,depth/2-.5]} color="#527e88" emissive="#527e88" intensity={.22} radius={.006}/>)}
    <SoftBox size={[width-.25,.5,.17]} position={[0,.25,-1]} color="#344651" radius={.06}/>
    {Array.from({length:Math.max(3,Math.round(width/5))},(_,i)=>{const count=Math.max(3,Math.round(width/5)),x=(i-(count-1)/2)*(width-.8)/count;return <group key={i} position={[x,0,-1]}><SoftBox size={[(width-.9)/count-.13,.06,.09]} position={[0,1.9,0]} color="#5c7380" radius={.02}/><SoftBox size={[.07,1.8,.08]} position={[-(width-.9)/count/2,.95,0]} color="#526975" radius={.02}/><mesh position={[0,1.2,-.02]}><boxGeometry args={[(width-.9)/count-.13,1.3,.035]}/><meshStandardMaterial color="#47707b" transparent opacity={.12} depthWrite={false} roughness={.4}/></mesh></group>})}
    {[-1,1].map(side=><Plant key={side} position={[side*(width/2-.8),.03,depth-1.3]} size={1.0}/>)}
    <FilingCabinet position={[-width/2+.6,.02,-.55]} accent="#8cbdb7"/>
  </group>
}

function Scene({ agents, categories, workloads = {}, interactions = [], selected, onSelect, reducedMotion, resetKey, active = true }: WorldProps) {
  const controls=useRef<OrbitControlsImpl>(null),[hovered,setHovered]=useState<string|null>(null)
  const {camera,size}=useThree()
  const namedAgents=useMemo(()=>{const counts=new Map<string,number>();for(const agent of agents){const name=agent.name||`${ROLE_NAME[agentRole(agent)]} agent`;counts.set(name,(counts.get(name)??0)+1)}return agents.map(agent=>counts.get(agent.name||`${ROLE_NAME[agentRole(agent)]} agent`)!>1?{...agent,tagId:agent.id.slice(-4)}:agent)},[agents])
  const layout=useMemo(()=>categoryLayout(namedAgents,categories),[namedAgents,categories])
  const {roomWidth,roomDepth}=layout
  const realInteractions=useMemo(()=>{const used=new Set<string>();return [...interactions].sort((a,b)=>(b.completed_at||'').localeCompare(a.completed_at||'')).filter(item=>{if(!item.id||item.from_agent_id===item.to_agent_id||!layout.locations.has(item.from_agent_id)||!layout.locations.has(item.to_agent_id)||!interactionPhase(item).active||used.has(item.from_agent_id))return false;used.add(item.from_agent_id);return true})},[interactions,layout.locations])
  const roomScale=Math.max(1,(roomWidth*.83+roomDepth*.558)/20.61,((roomWidth*.558+roomDepth*.83)*.449+2.5)/11.07)
  const aspectScale=size.width>0&&size.height>0?Math.max(1,1.6/(size.width/size.height)):1
  const fitScale=roomScale*aspectScale,cameraTarget=useMemo<Point>(()=>[0,.35,roomDepth*.53],[roomDepth])
  const labelScale=Math.max(.67,Math.min(1,1.15/roomScale))
  useCursor(hovered!==null)
  useEffect(()=>{if(!active)setHovered(null)},[active])
  useEffect(()=>{
    const orbit=controls.current;if(!orbit||!active||size.width<=0||size.height<=0)return
    const damping=orbit.enableDamping;orbit.enableDamping=false;orbit.target.set(...cameraTarget)
    camera.position.set(cameraTarget[0]+(CAMERA_POSITION[0]-CAMERA_TARGET[0])*fitScale,cameraTarget[1]+(CAMERA_POSITION[1]-CAMERA_TARGET[1])*fitScale,cameraTarget[2]+(CAMERA_POSITION[2]-CAMERA_TARGET[2])*fitScale)
    if(camera instanceof THREE.PerspectiveCamera){camera.far=Math.max(150,20.37*fitScale+70);camera.updateProjectionMatrix()}
    orbit.update();orbit.enableDamping=damping;orbit.saveState()
  },[camera,cameraTarget,fitScale,resetKey,active,size.width,size.height])
  useFrame(({camera})=>{const target=controls.current?.target;if(!target)return;const x=THREE.MathUtils.clamp(target.x,-roomWidth*.45,roomWidth*.45),y=THREE.MathUtils.clamp(target.y,.05,2.2),z=THREE.MathUtils.clamp(target.z,-.5,roomDepth+.5);camera.position.x+=x-target.x;camera.position.y+=y-target.y;camera.position.z+=z-target.z;target.set(x,y,z)})
  return <>
    <fog attach="fog" args={['#0d141c',38*fitScale,74*fitScale]}/>
    <ambientLight intensity={.62} color="#bfccd3"/><hemisphereLight args={['#b7d7e8','#182733',1.35]}/>
    <directionalLight position={[-7,16,12]} intensity={2.15} color="#e4eee8" castShadow shadow-mapSize={[2048,2048]} shadow-camera-left={-Math.max(12,roomWidth*.65)} shadow-camera-right={Math.max(12,roomWidth*.65)} shadow-camera-top={Math.max(10,roomDepth*.8)} shadow-camera-bottom={-Math.max(10,roomDepth*.8)} shadow-camera-far={Math.max(60,roomDepth+30)} shadow-bias={-.0004} shadow-normalBias={.025}/>
    <directionalLight position={[7,7,-7]} intensity={1.15} color="#8da8c7"/><directionalLight position={[4,3,10]} intensity={.3} color="#a5c2bd"/>
    <mesh position={[0,-1,roomDepth/2]} rotation={[-Math.PI/2,0,0]} receiveShadow><planeGeometry args={[180,180]}/><shadowMaterial transparent opacity={.21}/></mesh>
    <Architecture width={roomWidth} depth={roomDepth}/><OperationsHub position={layout.hubPosition} activeCount={agents.filter(agent=>agent.status==='running'||(workloads[agent.id]?.running_jobs??0)>0).length} reducedMotion={reducedMotion}/>
    {layout.zones.map(zone=><CategoryIsland key={zone.category.id} zone={zone} locations={layout.locations} selected={selected} hovered={hovered} workloads={workloads} interactions={realInteractions} reducedMotion={reducedMotion} labelScale={labelScale} onSelect={onSelect} onHover={setHovered}/>)}
    {realInteractions.map(interaction=><RecordedReview key={interaction.id} interaction={interaction} from={layout.locations.get(interaction.from_agent_id)!} to={layout.locations.get(interaction.to_agent_id)!} reducedMotion={reducedMotion}/>)}
    <OrbitControls ref={controls} makeDefault enabled={active} target={cameraTarget} enableDamping={!reducedMotion} dampingFactor={.07} minDistance={13} maxDistance={Math.max(90,30*fitScale)} minPolarAngle={.36} maxPolarAngle={1.18} minAzimuthAngle={-.85} maxAzimuthAngle={1.0} enablePan panSpeed={.35} rotateSpeed={.52} zoomSpeed={.62}/>
  </>
}

export default function World(props: WorldProps) {
  return <Canvas shadows frameloop={props.active === false ? 'never' : props.reducedMotion ? 'demand' : 'always'} camera={{ position: CAMERA_POSITION, fov: 36, near: .1, far: 150 }} dpr={[1, 1.7]} gl={{ antialias: true, alpha: true, powerPreference: 'high-performance' }} style={{ width: '100%', height: '100%', touchAction: 'none' }} role="region" aria-label={`Interactive LocalOps office with ${props.agents.length} individual agent characters grouped by category. Drag to orbit, scroll to zoom, or select any named agent. Warm colors and smoke visualize workload, not measured GPU temperature. Walks replay recorded collaboration events.`}>
    <Scene {...props} />
  </Canvas>
}

/** A detail-page portrait uses the same real-state mascot without HTML portals. */
export function AgentPortrait({ role, status, id = role, reducedMotion = false, active = true }: {
  role: string; status: string; id?: string; reducedMotion?: boolean; active?: boolean
}) {
  const agent = { id, role, status }
  const color = agentColor(agent)
  return <Canvas shadows frameloop={!active ? 'never' : reducedMotion ? 'demand' : 'always'} camera={{ position: [2.1, 1.1, 4.8], fov: 34, near: .1, far: 30 }} dpr={[1, 1.5]} gl={{ antialias: true, alpha: true }} style={{ width: '100%', height: '100%', pointerEvents: 'none' }} role="img" aria-label={`${ROLE_NAME[agentRole(agent)]} companion, ${status}`}>
    <ambientLight intensity={.85} color="#c7d8dc" />
    <hemisphereLight args={['#d9ebe8', '#233540', 1.25]} />
    <directionalLight position={[-3, 6, 4]} intensity={2} color="#e6ece6" castShadow shadow-mapSize={[512, 512]} shadow-camera-left={-2} shadow-camera-right={2} shadow-camera-top={3} shadow-camera-bottom={-2} shadow-normalBias={.025} />
    <directionalLight position={[3, 3, -3]} intensity={1.1} color="#99afce" />
    <group position={[0, -1.12, 0]} rotation={[0, .23, 0]}>
      <mesh position={[0, .05, 0]} castShadow receiveShadow><cylinderGeometry args={[1.12, 1.18, .1, 48]} /><meshStandardMaterial color="#293e48" roughness={.6} metalness={.2} /></mesh>
      <mesh position={[0, .106, 0]} rotation={[-Math.PI / 2, 0, 0]}><torusGeometry args={[1.04, .014, 5, 48]} /><meshStandardMaterial color={color} emissive={color} emissiveIntensity={.3} /></mesh>
      <Mascot role={agentRole(agent)} color={color} status={status} reducedMotion={reducedMotion} seed={agentSeed(id)} />
    </group>
  </Canvas>
}
