import { useEffect, useMemo, useRef, useState } from 'react'
import { Canvas, ThreeEvent, useFrame, useThree } from '@react-three/fiber'
import { Html, OrbitControls, RoundedBox, useCursor } from '@react-three/drei'
import * as THREE from 'three'
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib'

export type WorldProps = {
  agents: Array<{ id: string; role: string; status: string }>
  selected: string | null
  onSelect: (role: string) => void
  reducedMotion: boolean
  resetKey: number
  active?: boolean
}

type Role = 'hr' | 'finance' | 'support' | 'security' | 'optimizer'
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
const ROLE_NAME: Record<Role, string> = { hr: 'HR', finance: 'Finance', support: 'Support', security: 'Security', optimizer: 'Optimizer' }
const normalizeRole = (role: string): string => {
  const value = role.toLowerCase()
  if (value.includes('hr') || value.includes('human')) return 'hr'
  if (value.includes('finance') || value.includes('invoice')) return 'finance'
  if (value.includes('support')) return 'support'
  if (value.includes('security') || value.includes('guardian')) return 'security'
  if (value.includes('optim')) return 'optimizer'
  return value
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
    <SoftBox size={[.75, .035, .29]} position={[.15, .999, .24]} color="#3a4e5a" radius={.027} />
    {[0, 1, 2].map(row => <SoftBox key={row} size={[.62, .006, .012]} position={[.15, 1.022, .17 + row * .073]} color="#8898a0" radius={.002} />)}
    <SoftBox size={[.19, .065, .26]} position={[.74, 1.015, .25]} color="#ced4d0" radius={.04} />
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

function Mascot({ role, color, status, reducedMotion }: { role: Role; color: string; status: string; reducedMotion: boolean }) {
  const root = useRef<THREE.Group>(null)
  const head = useRef<THREE.Group>(null)
  const left = useRef<THREE.Group>(null)
  const right = useRef<THREE.Group>(null)
  const stateAt = useRef(0)
  useEffect(() => { stateAt.current = performance.now() / 1000 }, [status])
  useFrame(({ clock }, delta) => {
    if (!root.current || !head.current || !left.current || !right.current) return
    const t = clock.elapsedTime
    const running = status === 'running'
    const celebrating = status === 'completed' && performance.now() / 1000 - stateAt.current < 2.4
    const breathing = reducedMotion ? 0 : Math.sin(t * 1.8) * .012
    const bounce = !reducedMotion && celebrating ? Math.max(0, Math.sin((performance.now() / 1000 - stateAt.current) * 8)) * .16 : 0
    root.current.position.y = .17 + breathing + bounce
    root.current.rotation.z = reducedMotion ? 0 : Math.sin(t * 1.4) * .008
    head.current.rotation.y = THREE.MathUtils.damp(head.current.rotation.y, !reducedMotion && status === 'queued' ? Math.sin(t * .7) * .24 : running ? -.08 : .07, 5, delta)
    head.current.rotation.x = THREE.MathUtils.damp(head.current.rotation.x, running ? .08 : status === 'paused' ? -.055 : 0, 5, delta)
    left.current.rotation.x = THREE.MathUtils.damp(left.current.rotation.x, running ? -.38 + (reducedMotion ? 0 : Math.sin(t * 5) * .1) : -.12, 6, delta)
    right.current.rotation.x = THREE.MathUtils.damp(right.current.rotation.x, running ? -.7 + (reducedMotion ? 0 : Math.sin(t * 5 + 1.4) * .18) : -.13, 6, delta)
    right.current.rotation.z = THREE.MathUtils.damp(right.current.rotation.z, celebrating ? -.95 : status === 'queued' ? -.25 : -.11, 5, delta)
    left.current.rotation.z = THREE.MathUtils.damp(left.current.rotation.z, celebrating ? .38 : .12, 5, delta)
  })
  const alert = ['error', 'blocked', 'security_blocked'].includes(status)
  const indicator = alert || status === 'queued' ? '#e2b779' : status === 'completed' ? '#83c5a7' : status === 'paused' ? '#8395a4' : color
  return <group ref={root} position={[0, .17, 0]}>
    <Ball position={[-.21, .12, .11]} radius={.18} scale={[.86, .64, 1.45]} />
    <Ball position={[.21, .12, .11]} radius={.18} scale={[.86, .64, 1.45]} />
    <mesh position={[-.2, .35, 0]} castShadow><capsuleGeometry args={[.135, .21, 5, 12]} /><meshStandardMaterial color={WHITE} roughness={.65} /></mesh>
    <mesh position={[.2, .35, 0]} castShadow><capsuleGeometry args={[.135, .21, 5, 12]} /><meshStandardMaterial color={WHITE} roughness={.65} /></mesh>
    <Ball position={[0, .77, 0]} radius={.43} scale={[1, 1.24, .92]} />
    <SoftBox size={[.29, .08, .11]} position={[0, 1.05, .33]} color={color} radius={.03} />
    <Ball position={[0, 1.09, .37]} radius={.035} color="#dcece7" />
    <group ref={head} position={[0, 1.56, 0]}>
      <Ball position={[0, 0, 0]} radius={.55} scale={[1.04, .96, 1]} />
      <Ball position={[-.56, -.04, 0]} radius={.105} scale={[.7, 1, .82]} />
      <Ball position={[.56, -.04, 0]} radius={.105} scale={[.7, 1, .82]} />
      <Ball position={[-.165, .035, .523]} radius={.045} color="#17232c" scale={[.92, 1.12, .42]} />
      <Ball position={[.165, .035, .523]} radius={.045} color="#17232c" scale={[.92, 1.12, .42]} />
      <Ball position={[-.22, -.087, .499]} radius={.048} color="#cfdbd7" scale={[1, .46, .15]} />
      <Ball position={[.22, -.087, .499]} radius={.048} color="#cfdbd7" scale={[1, .46, .15]} />
      <mesh position={[0, -.115, .526]} rotation={[0, 0, Math.PI]}>
        <torusGeometry args={[alert ? .09 : .115, .012, 5, 18, Math.PI]} />
        <meshStandardMaterial color="#26343b" roughness={.8} />
      </mesh>
      <mesh position={[.016, .519, -.05]} rotation={[.18, 0, -.2]} castShadow><capsuleGeometry args={[.063, .13, 4, 10]} /><meshStandardMaterial color={WHITE} roughness={.7} /></mesh>
      {role === 'support' && <group>
        <mesh position={[0, -.02, 0]}><torusGeometry args={[.583, .031, 6, 28, Math.PI]} /><meshStandardMaterial color="#3a5160" roughness={.5} /></mesh>
        {[-1, 1].map(side => <SoftBox key={side} size={[.105, .23, .21]} position={[side * .59, -.045, 0]} color="#3a5160" radius={.04} />)}
        <Cable points={[[.59, -.11, .08], [.57, -.22, .29], [.3, -.24, .51]]} color="#3c5360" radius={.025} />
        <Ball position={[.3, -.24, .51]} radius={.044} color={color} />
      </group>}
    </group>
    <group ref={left} position={[-.445, 1.04, 0]} rotation={[0, 0, .12]}>
      <mesh position={[0, -.16, 0]} castShadow><capsuleGeometry args={[.13, .27, 5, 12]} /><meshStandardMaterial color={WHITE} roughness={.64} /></mesh>
      <Ball position={[0, -.36, .015]} radius={.145} />
      <Accessory role={role} color={color} />
    </group>
    <group ref={right} position={[.445, 1.04, 0]} rotation={[0, 0, -.11]}>
      <mesh position={[0, -.16, 0]} castShadow><capsuleGeometry args={[.13, .27, 5, 12]} /><meshStandardMaterial color={WHITE} roughness={.64} /></mesh>
      <Ball position={[0, -.36, .015]} radius={.145} />
    </group>
    <group position={[.72, 2.13, .02]}>
      <Ball position={[0, 0, 0]} radius={.074} color={indicator} emissive={indicator} intensity={.45} />
      {(alert || status === 'queued') && <mesh rotation={[0, 0, .15]}><torusGeometry args={[.12, .011, 5, 20]} /><meshStandardMaterial color={indicator} /></mesh>}
      {status === 'queued' && <group position={[0, 0, .078]}>
        <SoftBox size={[.013, .065, .01]} position={[0, .026, 0]} color="#354048" radius={.003} />
        <SoftBox size={[.053, .013, .01]} position={[.022, 0, 0]} color="#354048" radius={.003} />
      </group>}
    </group>
  </group>
}

function Station({ zone, status, selected, hovered, reducedMotion, compactLabels, onSelect, onHover }: {
  zone: (typeof ZONES)[number]; status: string; selected: boolean; hovered: boolean; reducedMotion: boolean; compactLabels: boolean
  onSelect: (role: string) => void; onHover: (role: string | null) => void
}) {
  const alert = ['error', 'blocked', 'security_blocked'].includes(status)
  const accent = alert ? '#dfb176' : zone.color
  const handleSelect = (event: ThreeEvent<MouseEvent>) => { event.stopPropagation(); onSelect(zone.role) }
  return <group position={zone.position}
    onClick={handleSelect}
    onPointerOver={event => { event.stopPropagation(); onHover(zone.role) }}
    onPointerOut={() => onHover(null)}>
    <SoftBox size={[4.4, .20, 3.65]} position={[0, .03, -.15]} color={selected ? '#334a53' : hovered ? '#30404c' : '#273540'} radius={.18} />
    <SoftBox size={[4.17, .027, 3.39]} position={[0, .142, -.15]} color="#30414c" radius={.14} />
    <SoftBox size={[3.9, .018, .025]} position={[0, .166, 1.57]} color={accent} emissive={accent} intensity={selected ? 1 : .27} radius={.007} />
    {selected && <group>
      <SoftBox size={[.025, .02, 3.05]} position={[-2.04, .166, -.15]} color={accent} emissive={accent} intensity={.6} radius={.007} />
      <SoftBox size={[.025, .02, 3.05]} position={[2.04, .166, -.15]} color={accent} emissive={accent} intensity={.6} radius={.007} />
    </group>}
    <group position={[0, .15, 0]}>
      <Desk accent={accent} role={zone.role} />
      <group position={[.12, 0, .95]} rotation={[0, .20, 0]}><Mascot role={zone.role} color={zone.color} status={status} reducedMotion={reducedMotion} /></group>
      {zone.role === 'hr' && <FilingCabinet position={[-1.62, 0, -.73]} accent={accent} />}
      {zone.role === 'finance' && <group position={[-1.62, 0, -.77]}>
        <SoftBox size={[.72, .9, .68]} position={[0, .46, 0]} color="#536371" radius={.07} />
        <SoftBox size={[.63, .018, .5]} position={[0, .93, .025]} color="#b7c1bd" radius={.02} />
        <SoftBox size={[.43, .1, .29]} position={[0, .96, -.04]} color="#dee0d4" radius={.02} />
        <SoftBox size={[.28, .029, .18]} position={[0, .66, .35]} color="#263847" radius={.015} />
      </group>}
      {zone.role === 'support' && <MessageWall accent={accent} />}
      {zone.role === 'security' && <group position={[-1.62, 1.18, -.82]}><SoftBox size={[.72, 1.25, .28]} position={[0, -.51, -.14]} color="#384c58" radius={.08} /><Shield color={accent} scale={1.15} /></group>}
      {zone.role === 'optimizer' && <WorkloadTracks accent={accent} active={status === 'running'} reducedMotion={reducedMotion} />}
      <Plant position={[1.65, 0, -.95]} size={zone.role === 'optimizer' ? .6 : .76} />
      <SoftBox size={[.53, .04, .43]} position={[-1.54, .06, .94]} color="#374b56" radius={.05} />
      <SoftBox size={[.47, .26, .37]} position={[-1.54, .18, .94]} color="#62737c" radius={.07} />
    </group>
    <Html position={zone.role === 'optimizer' && !compactLabels ? [2.3, 1.35, -2.2] : [0, .22, 1.98]} center style={{ pointerEvents: 'auto', whiteSpace: 'nowrap' }}>
      <button type="button" aria-label={`Open ${ROLE_NAME[zone.role]} agent, ${status}`} onClick={() => onSelect(zone.role)}
        onMouseEnter={() => onHover(zone.role)} onMouseLeave={() => onHover(null)}
        style={{ padding: compactLabels ? '5px 7px' : '5px 9px', border: `1px solid ${selected ? accent : '#69828b33'}`, borderRadius: 6, color: '#ecf2f2', background: selected ? '#243b42e8' : '#13202be8', cursor: 'pointer', fontFamily: 'inherit', textAlign: 'left', boxShadow: '0 5px 20px #0003', minWidth: compactLabels ? 55 : 86 }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: compactLabels ? 4 : 6, fontSize: compactLabels ? 9 : 10, fontWeight: 650, letterSpacing: '.025em' }}>
          <span style={{ width: 5, height: 5, background: accent, borderRadius: '50%', display: 'inline-block', boxShadow: status === 'running' ? `0 0 7px ${accent}` : 'none' }} />{zone.label}
          {!compactLabels && <span style={{ marginLeft: 'auto', fontSize: 10, opacity: .4 }}>↗</span>}
        </span>
        {!compactLabels && <span style={{ display: 'block', marginTop: 3, fontSize: 6, color: '#8b9da8', letterSpacing: '.07em' }}>{zone.subtitle}</span>}
      </button>
    </Html>
  </group>
}

function OperationsHub({ activeCount, reducedMotion }: { activeCount: number; reducedMotion: boolean }) {
  const ring = useRef<THREE.Group>(null)
  useFrame(({ clock }) => { if (ring.current && !reducedMotion) ring.current.rotation.y = clock.elapsedTime * .065 })
  return <group position={[-.15, .04, 1.28]}>
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

function Architecture() {
  return <group>
    <SoftBox size={[17.1, .43, 11.5]} position={[-.15, -.28, -.2]} color="#16252f" radius={.22} />
    <SoftBox size={[16.83, .045, 11.23]} position={[-.15, -.035, -.2]} color="#1c2d37" radius={.2} />
    <SoftBox size={[16.45, .026, .022]} position={[-.15, -.155, 5.557]} color="#6b9299" emissive="#527e88" intensity={.25} radius={.007} />
    <SoftBox size={[.022, .026, 10.88]} position={[8.37, -.155, -.2]} color="#537e85" emissive="#527e88" intensity={.2} radius={.007} />
    {[-7.7, 7.4].map(x => [-4.65, 4.24].map(z => <mesh key={`${x}-${z}`} position={[x, -.52, z]} castShadow><cylinderGeometry args={[.24, .18, .5, 12]} /><meshStandardMaterial color="#263741" roughness={.55} metalness={.4} /></mesh>))}
    <SoftBox size={[16.75, .53, .18]} position={[-.15, .25, -5.72]} color="#344651" radius={.065} />
    {[-7.94, -2.65, 2.63, 7.63].map(x => <SoftBox key={x} size={[.09, 1.93, .10]} position={[x, .95, -5.73]} color="#516570" radius={.025} />)}
    {[-5.3, 0, 5.3].map(x => <group key={x}>
      <mesh position={[x, 1.17, -5.74]}><boxGeometry args={[5.16, 1.34, .036]} /><meshStandardMaterial color="#47707b" transparent opacity={.12} roughness={.4} metalness={.18} depthWrite={false} /></mesh>
      <SoftBox size={[5.19, .06, .09]} position={[x, 1.93, -5.73]} color="#5c7380" radius={.022} />
    </group>)}
    <SoftBox size={[16.5, .022, .034]} position={[-.15, .55, -5.61]} color="#5c9eaa" emissive="#5c9eaa" intensity={.25} radius={.006} />
    <Plant position={[-7.9, .03, 4.3]} size={1.2} />
    <Plant position={[7.5, .03, 4.2]} size={1.14} />
    <SoftBox size={[.77, 1.85, .82]} position={[-7.62, .94, -4.75]} color="#2d414e" radius={.09} />
    {[.34, .62, .9, 1.18, 1.46].map((y, i) => <group key={y}>
      <SoftBox size={[.59, .1, .027]} position={[-7.62, y, -4.323]} color="#4a626e" radius={.025} />
      <Ball position={[-7.83, y, -4.3]} radius={.02} color={i === 0 ? '#baafdc' : '#78b7a9'} emissive="#78b7a9" intensity={.3} />
    </group>)}
    <SoftBox size={[1.31, .055, .30]} position={[6.77, .81, -5.47]} color="#627680" radius={.045} />
    <Plant position={[6.35, .86, -5.49]} size={.62} />
    <SoftBox size={[.22, .29, .14]} position={[7.12, 1.02, -5.49]} color="#b7b9b8" radius={.025} />
    <SoftBox size={[.14, .19, .014]} position={[7.12, 1.035, -5.409]} color="#718fa1" radius={.025} />
    <Cable points={[[-3.34, .015, 2.5], [-2.65, .015, 2.5], [-2.1, .015, 1.55], [-1.89, .015, 1.28]]} color="#416d76" radius={.017} emissive />
    <Cable points={[[-3.34, .015, -2.35], [-2.78, .015, -2.35], [-2.74, .015, -.05], [-1.71, .015, .39]]} color="#4d526f" radius={.017} emissive />
    <Cable points={[[-.15, .015, -1.5], [-.15, .015, -.4], [-.15, .015, -.1]]} color="#416d76" radius={.017} emissive />
    <Cable points={[[3.02, .015, -2.35], [2.42, .015, -2.35], [2.42, .015, .02], [1.43, .015, .43]]} color="#4d626b" radius={.017} emissive />
    <Cable points={[[3.02, .015, 2.5], [2.28, .015, 2.5], [1.75, .015, 1.55], [1.56, .015, 1.28]]} color="#416d76" radius={.017} emissive />
  </group>
}

function Scene({ agents, selected, onSelect, reducedMotion, resetKey, active = true }: WorldProps) {
  const controls = useRef<OrbitControlsImpl>(null)
  const [hovered, setHovered] = useState<string | null>(null)
  const { camera, size } = useThree()
  const fitScale = size.width > 0 && size.height > 0 ? Math.max(1, 1.6 / (size.width / size.height)) : 1
  useCursor(hovered !== null)
  useEffect(() => { if (!active) setHovered(null) }, [active])
  useEffect(() => {
    const orbit = controls.current
    if (!orbit || !active || size.width <= 0 || size.height <= 0) return
    // A portrait canvas needs more distance to retain the whole office width.
    // Reset uses this fitted view; desktop composition stays exactly the same.
    const damping = orbit.enableDamping
    orbit.enableDamping = false
    orbit.target.set(...CAMERA_TARGET)
    camera.position.set(
      CAMERA_TARGET[0] + (CAMERA_POSITION[0] - CAMERA_TARGET[0]) * fitScale,
      CAMERA_TARGET[1] + (CAMERA_POSITION[1] - CAMERA_TARGET[1]) * fitScale,
      CAMERA_TARGET[2] + (CAMERA_POSITION[2] - CAMERA_TARGET[2]) * fitScale,
    )
    orbit.update()
    orbit.enableDamping = damping
    orbit.saveState()
  }, [camera, fitScale, resetKey, active, size.width, size.height])
  useFrame(({ camera }) => {
    const target = controls.current?.target
    if (!target) return
    const x = THREE.MathUtils.clamp(target.x, -2.8, 2.8)
    const y = THREE.MathUtils.clamp(target.y, .05, 1.8)
    const z = THREE.MathUtils.clamp(target.z, -2.8, 2.8)
    camera.position.x += x - target.x
    camera.position.y += y - target.y
    camera.position.z += z - target.z
    target.set(x, y, z)
  })
  return <>
    <fog attach="fog" args={['#0d141c', 38 * fitScale, 74 * fitScale]} />
    <ambientLight intensity={.62} color="#bfccd3" />
    <hemisphereLight args={['#b7d7e8', '#182733', 1.35]} />
    <directionalLight position={[-7, 13, 9]} intensity={2.15} color="#e4eee8" castShadow shadow-mapSize={[2048, 2048]} shadow-camera-left={-12} shadow-camera-right={12} shadow-camera-top={10} shadow-camera-bottom={-10} shadow-camera-near={.5} shadow-camera-far={38} shadow-bias={-.0004} shadow-normalBias={.025} />
    <directionalLight position={[7, 7, -7]} intensity={1.15} color="#8da8c7" />
    <directionalLight position={[4, 3, 10]} intensity={.3} color="#a5c2bd" />
    <mesh position={[0, -1, 0]} rotation={[-Math.PI / 2, 0, 0]} receiveShadow><planeGeometry args={[180, 180]} /><shadowMaterial transparent opacity={.21} /></mesh>
    <Architecture />
    <OperationsHub activeCount={agents.filter(a => a.status === 'running').length} reducedMotion={reducedMotion} />
    {ZONES.map(zone => {
      const agent = agents.find(a => normalizeRole(a.role) === zone.role)
      return <Station key={zone.role} zone={zone} status={agent?.status ?? 'idle'} selected={normalizeRole(selected ?? '') === zone.role || selected === agent?.id} hovered={hovered === zone.role} reducedMotion={reducedMotion} compactLabels={fitScale > 1} onSelect={onSelect} onHover={setHovered} />
    })}
    <OrbitControls ref={controls} makeDefault enabled={active} target={CAMERA_TARGET} enableDamping={!reducedMotion} dampingFactor={.07} minDistance={13} maxDistance={Math.max(60, 30 * fitScale)} minPolarAngle={.36} maxPolarAngle={1.18} minAzimuthAngle={-.85} maxAzimuthAngle={1.0} enablePan panSpeed={.35} rotateSpeed={.52} zoomSpeed={.62} />
  </>
}

export default function World(props: WorldProps) {
  return <Canvas shadows frameloop={props.active === false ? 'never' : props.reducedMotion ? 'demand' : 'always'} camera={{ position: CAMERA_POSITION, fov: 36, near: .1, far: 150 }} dpr={[1, 1.7]} gl={{ antialias: true, alpha: true, powerPreference: 'high-performance' }} style={{ width: '100%', height: '100%', touchAction: 'none' }} role="img" aria-label="Interactive miniature LocalOps AI office with five agent stations. Drag to orbit, scroll to zoom, or click an agent to open its workflow.">
    <Scene {...props} />
  </Canvas>
}
