"use client";
import { useEffect, useRef } from "react";
import * as THREE from "three";

export function AuroraScene() {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let raf = 0;
    let visible = true;
    let stop: (() => void) | undefined;
    try {
      const canvas = ref.current!;
      const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: false });
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
      const scene = new THREE.Scene();
      const cam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
      const uniforms = { uTime: { value: 0 }, uPointer: { value: new THREE.Vector2(0.5, 0.5) } };
      const mesh = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), new THREE.ShaderMaterial({
        uniforms, transparent: true,
        vertexShader: `void main(){ gl_Position = vec4(position, 1.0); }`,
        fragmentShader: `
          uniform float uTime; uniform vec2 uPointer;
          float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
          float noise(vec2 p){ vec2 i = floor(p), f = fract(p); f = f*f*(3.-2.*f); return mix(mix(hash(i), hash(i+vec2(1,0)), f.x), mix(hash(i+vec2(0,1)), hash(i+vec2(1,1)), f.x), f.y); }
          void main(){
            vec2 uv = gl_FragCoord.xy / min(resolution.x, resolution.y);
            float t = uTime * 0.06;
            float n = noise(uv * 2.2 + vec2(t, -t * 0.7)) * 0.6 + noise(uv * 5.0 - t) * 0.4;
            float band = smoothstep(0.25, 0.75, n + 0.15 * uPointer.y);
            vec3 col = mix(vec3(0.486, 0.423, 1.0), vec3(0.22, 0.882, 1.0), band);
            float d = length(uv - vec2(0.62, 0.42));
            float shield = exp(-18.0 * abs(d - 0.34)) * 0.9;
            float glow = exp(-4.5 * d) * 0.35;
            float a = (band * 0.12 + shield * 0.55 + glow) * smoothstep(1.2, 0.2, d);
            gl_FragColor = vec4(col * a, a);
          }
        `.replace("resolution", "vec2(1.0, 1.0)"),
      }));
      scene.add(mesh);
      const io = new IntersectionObserver(([e]) => (visible = e.isIntersecting)); io.observe(canvas);
      const onMove = (e: PointerEvent) => uniforms.uPointer.value.set(e.clientX / innerWidth, 1 - e.clientY / innerHeight);
      addEventListener("pointermove", onMove);
      const clock = new THREE.Clock();
      stop = () => { cancelAnimationFrame(raf); io.disconnect(); removeEventListener("pointermove", onMove); renderer.dispose(); };
      (function tick() { raf = requestAnimationFrame(tick); if (visible) { uniforms.uTime.value = clock.getElapsedTime(); renderer.render(scene, cam); } })();
    } catch {
      // WebGL unavailable or blocked (hardware acceleration off, GPU blocklist,
      // RDP/VM): the aurora is purely decorative — degrade to the static
      // backdrop instead of crashing the whole route.
      cancelAnimationFrame(raf);
      return;
    }
    return () => stop?.();
  }, []);
  return <canvas ref={ref} aria-hidden className="absolute inset-0 h-full w-full" />;
}