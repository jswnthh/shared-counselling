import { useEffect, useRef, useState, type CSSProperties, type PointerEvent } from "react";

const COUPON = { code: "PLAY10", discount: "10% off", description: "your first Shared Counselling session" };
const HOOP = { x: 52, rimY: 61 };
type Point = { x: number; y: number };
type Result = "made" | "missed" | null;
const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max);

function Basketball({ style }: { style: CSSProperties }) {
  return <span className="bc-ball" style={style} aria-hidden="true"><i /><i /><i /><i /></span>;
}

export default function App() {
  const courtRef = useRef<HTMLDivElement>(null), frameRef = useRef<number | null>(null);
  const startRef = useRef<Point>({ x: 17, y: 76 }), ballRef = useRef<Point>({ x: 17, y: 76 }), pointerRef = useRef<number | null>(null);
  const [score, setScore] = useState(0), [shots, setShots] = useState(5), [ball, setBall] = useState<Point>(startRef.current);
  const [aiming, setAiming] = useState(false), [flying, setFlying] = useState(false), [result, setResult] = useState<Result>(null);
  const [message, setMessage] = useState("Pull the ball back, then release."), [copied, setCopied] = useState(false);

  const resetBall = () => { const court = courtRef.current; if (!court) return; startRef.current = { x: court.clientWidth < 440 ? 16 : 17, y: 76 }; ballRef.current = startRef.current; setBall(ballRef.current); };
  useEffect(() => { resetBall(); window.addEventListener("resize", resetBall); return () => { window.removeEventListener("resize", resetBall); if (frameRef.current) cancelAnimationFrame(frameRef.current); }; }, []);
  const pointFromEvent = (event: PointerEvent) => { const rect = courtRef.current!.getBoundingClientRect(); return { x: ((event.clientX - rect.left) / rect.width) * 100, y: ((event.clientY - rect.top) / rect.height) * 100 }; };
  const moveAim = (point: Point) => { const start = startRef.current, dx = clamp(point.x - start.x, -28, 22), dy = clamp(point.y - start.y, -24, 25), next = { x: start.x + dx * .42, y: start.y + dy * .42 }; ballRef.current = next; setBall(next); };
  const completeShot = (made: boolean) => { setFlying(false); setResult(made ? "made" : "missed"); setShots(current => current - 1); if (made) setScore(current => current + 1); setMessage(made ? "Swish." : "Close — try a softer arc."); window.setTimeout(() => { setResult(null); resetBall(); }, window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 100 : 620); };
  const shoot = (release: Point) => {
    const start = startRef.current, pull = { x: clamp(start.x - release.x, -22, 28), y: clamp(start.y - release.y, -25, 27) };
    if (Math.hypot(pull.x, pull.y) < 7) { setMessage("Pull back a little farther to shoot."); resetBall(); return; }
    setFlying(true); setMessage(""); const velocity = { x: pull.x * .24, y: pull.y * .29 }, position = { ...ballRef.current }; let previous = { ...position }, last = performance.now(), elapsed = 0, scored = false, bounces = 0;
    const tick = (now: number) => { const dt = Math.min((now - last) / 1000, .03); last = now; elapsed += dt; previous = { ...position }; velocity.y += 4 * dt; position.x += velocity.x * dt * 10; position.y += velocity.y * dt * 10;
      const crossesRim = previous.y < HOOP.rimY && position.y >= HOOP.rimY && velocity.y > 0, insideRim = Math.abs(position.x - HOOP.x) < 5.8;
      if (!scored && crossesRim && insideRim) { scored = true; velocity.x *= .16; } else if (!scored && crossesRim && Math.abs(position.x - HOOP.x) < 9) { velocity.x = (position.x < HOOP.x ? -1 : 1) * Math.max(Math.abs(velocity.x) * .55, 2.4); velocity.y = -Math.max(Math.abs(velocity.y) * .42, 3.8); }
      if (!scored && position.y > 93 && velocity.y > 0) { position.y = 93; velocity.y *= -.38; velocity.x *= .7; bounces += 1; }
      ballRef.current = position; setBall({ ...position }); const throughNet = scored && position.y > 77, out = position.x < -10 || position.x > 110 || position.y > 108 || elapsed > 4.5 || (!scored && bounces > 1);
      if (throughNet || out) { completeShot(throughNet); return; } frameRef.current = requestAnimationFrame(tick); };
    frameRef.current = requestAnimationFrame(tick);
  };
  const onPointerDown = (event: PointerEvent<HTMLButtonElement>) => { if (flying || shots === 0 || score === 5) return; event.currentTarget.setPointerCapture(event.pointerId); pointerRef.current = event.pointerId; setAiming(true); setMessage("Aim away from the hoop, then release."); };
  const gameOver = shots === 0 || score === 5, unlocked = score === 5, guideLength = Math.hypot(ball.x - startRef.current.x, ball.y - startRef.current.y), guideAngle = Math.atan2(startRef.current.y - ball.y, startRef.current.x - ball.x) * 180 / Math.PI;
  const replay = () => { setScore(0); setShots(5); setResult(null); setCopied(false); setMessage("Pull the ball back, then release."); resetBall(); };
  return <section className="basketball-coupon" aria-label="Basketball coupon game"><header className="bc-heading"><div><h2>Pull back and<br />take your shot.</h2><p>Five baskets in five tries unlocks a little thank-you.</p></div><div className="bc-score" aria-label={`${score} baskets made, ${shots} shots remaining`}><span>Baskets <b>{score}/5</b></span><i /><span>Shots <b>{shots}</b></span></div></header><div className="bc-court" ref={courtRef} role="application" aria-label="Basketball game. Drag the ball away from the hoop and release to shoot."><div className="bc-surface"><p>Pull back and take your shot.</p><span className="bc-surface-target" aria-hidden="true" /></div>{aiming && <span className="bc-guide" style={{ left: `${ball.x}%`, top: `${ball.y}%`, width: `${guideLength * 1.6}%`, transform: `rotate(${guideAngle}deg)` }} />}<div className="bc-hoop" aria-hidden="true"><span className="bc-board" /><img className="bc-rim bc-rim-back" src="/static/basketball/assets/b8ea9.svg" alt="" /><img className="bc-net" src="/static/basketball/assets/0a1a2.svg" alt="" /><img className="bc-rim bc-rim-front" src="/static/basketball/assets/b92f1.svg" alt="" /></div><aside className={`bc-coupon-card ${unlocked ? "is-unlocked" : ""}`} aria-hidden={!unlocked}><span>{unlocked ? "UNLOCKED" : "10% OFF"}</span>{unlocked && <strong>{COUPON.code}</strong>}</aside><button className="bc-ball-button" type="button" onPointerDown={onPointerDown} onPointerMove={event => aiming && event.pointerId === pointerRef.current && moveAim(pointFromEvent(event))} onPointerUp={event => { if (aiming && event.pointerId === pointerRef.current) { setAiming(false); pointerRef.current = null; shoot(pointFromEvent(event)); } }} onPointerCancel={() => { setAiming(false); pointerRef.current = null; resetBall(); }} aria-label="Drag the basketball backwards and release to shoot" disabled={flying || gameOver} style={{ left: `${ball.x}%`, top: `${ball.y}%` }}><Basketball style={{ transform: `rotate(${(ball.x - startRef.current.x) * 3}deg)` }} /></button><p className={`bc-message ${result ? `is-${result}` : ""}`} aria-live="polite">{message}</p><button className="bc-keyboard-shot" type="button" disabled={flying || gameOver} onClick={() => { ballRef.current = startRef.current; shoot({ x: 8, y: 90 }); }}>Take a shot</button>{gameOver && <div className="bc-outcome" role="status">{unlocked ? <><p>Coupon unlocked</p><h3>Five clean baskets.</h3><span>Demo reward · {COUPON.discount}</span><code>{COUPON.code}</code><button type="button" onClick={async () => { await navigator.clipboard?.writeText(COUPON.code); setCopied(true); }}>{copied ? "Copied" : "Copy code"}</button></> : <><p>Round complete</p><h3>{score} of 5 baskets.</h3><span>Five made shots in five attempts unlocks the demo coupon.</span></>}<button className="bc-replay" type="button" onClick={replay}>Play again</button></div>}</div><p className="bc-note">Demo coupon only — a real offer needs server-side validation during booking.</p></section>;
}
