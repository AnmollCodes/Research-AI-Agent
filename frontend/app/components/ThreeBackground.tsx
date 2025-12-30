"use client";

import { useRef, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Points, PointMaterial } from "@react-three/drei";
import * as THREE from "three";

function ParticleField() {
    const ref = useRef<THREE.Points>(null!);

    const count = 3000; // Increased for density
    const positions = useMemo(() => {
        const pos = new Float32Array(count * 3);
        for (let i = 0; i < count; i++) {
            // Distribute in a sphere
            const r = 2.0;
            const theta = 2 * Math.PI * Math.random();
            const phi = Math.acos(2 * Math.random() - 1);
            const x = r * Math.sin(phi) * Math.cos(theta);
            const y = r * Math.sin(phi) * Math.sin(theta);
            const z = r * Math.cos(phi);
            pos[i * 3] = x;
            pos[i * 3 + 1] = y;
            pos[i * 3 + 2] = z;
        }
        return pos;
    }, []);

    useFrame((state, delta) => {
        if (ref.current) {
            // Slow rotation
            ref.current.rotation.x += delta * 0.03;
            ref.current.rotation.y += delta * 0.05;
            // Pulse effect
            const scale = 1 + Math.sin(state.clock.elapsedTime * 0.5) * 0.05;
            ref.current.scale.set(scale, scale, scale);
        }
    });

    return (
        <Points ref={ref} positions={positions} stride={3} frustumCulled={false}>
            <PointMaterial
                transparent
                color="#10b981" // Emerald green to match theme
                size={0.003}
                sizeAttenuation={true}
                depthWrite={false}
                opacity={0.8}
                blending={THREE.AdditiveBlending}
            />
        </Points>
    );
}

export default function ThreeBackground() {
    return (
        <div className="fixed inset-0 -z-10 bg-[#050505]">
            <Canvas camera={{ position: [0, 0, 1.2], fov: 60 }}>
                <fog attach="fog" args={['#050505', 1, 3]} />
                <ParticleField />
            </Canvas>
            {/* Vignette & Gradient Overlay */}
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,rgba(0,0,0,0.8)_100%)] pointer-events-none" />
            <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-[#050505] pointer-events-none" />
        </div>
    );
}
