"use client";
/**
 * Motion primitives — reusable, accessible building blocks.
 * Copy to src/components/motion/ and import these everywhere instead of
 * writing one-off animations.
 *
 * Requires:  npm install motion lenis
 * Framer Motion is imported from "motion/react".
 *
 * --------------------------------------------------------------------------
 * LENIS SMOOTH SCROLL — set this up ONCE at your app root (layout/_app):
 *
 *   "use client";
 *   import { useEffect } from "react";
 *   import Lenis from "lenis";
 *   export function SmoothScroll({ children }) {
 *     useEffect(() => {
 *       const lenis = new Lenis({ duration: 1.1, smoothWheel: true });
 *       let raf: number;
 *       const loop = (t: number) => { lenis.raf(t); raf = requestAnimationFrame(loop); };
 *       raf = requestAnimationFrame(loop);
 *       return () => { cancelAnimationFrame(raf); lenis.destroy(); };
 *     }, []);
 *     return <>{children}</>;
 *   }
 * --------------------------------------------------------------------------
 */

import { useRef } from "react";
import {
  motion,
  useScroll,
  useTransform,
  useReducedMotion,
  type Variants,
} from "motion/react";
import { ease, duration, stagger, spring, fadeUp } from "@/lib/motion-tokens";

/* -------------------------------------------------------------------------- */
/* <Reveal> — fade + rise into view as it scrolls in.                          */
/* -------------------------------------------------------------------------- */
export function Reveal({
  children,
  delay = 0,
  y = 24,
  once = true,
  className,
}: {
  children: React.ReactNode;
  delay?: number;
  y?: number;
  once?: boolean;
  className?: string;
}) {
  const reduce = useReducedMotion();
  const variants: Variants = {
    hidden: { opacity: 0, y: reduce ? 0 : y },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: duration.base, ease: ease.out, delay },
    },
  };
  return (
    <motion.div
      className={className}
      variants={variants}
      initial="hidden"
      whileInView="visible"
      viewport={{ once, margin: "-10% 0px -10% 0px" }}
    >
      {children}
    </motion.div>
  );
}

/* -------------------------------------------------------------------------- */
/* <Stagger> + <StaggerItem> — children reveal one after another.             */
/* Wrap items in <StaggerItem>.                                               */
/* -------------------------------------------------------------------------- */
export function Stagger({
  children,
  interval = stagger.base,
  once = true,
  className,
}: {
  children: React.ReactNode;
  interval?: number;
  once?: boolean;
  className?: string;
}) {
  return (
    <motion.div
      className={className}
      variants={{ hidden: {}, visible: { transition: { staggerChildren: interval } } }}
      initial="hidden"
      whileInView="visible"
      viewport={{ once, margin: "-10% 0px -10% 0px" }}
    >
      {children}
    </motion.div>
  );
}

export function StaggerItem({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  const reduce = useReducedMotion();
  return (
    <motion.div className={className} variants={reduce ? fadeUpReduced : fadeUp}>
      {children}
    </motion.div>
  );
}
const fadeUpReduced: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { duration: duration.base, ease: ease.out } },
};

/* -------------------------------------------------------------------------- */
/* <Parallax> — element drifts as you scroll past it.                         */
/* speed > 0 moves down, < 0 moves up. Keep subtle (e.g. 0.15–0.4).           */
/* -------------------------------------------------------------------------- */
export function Parallax({
  children,
  speed = 0.3,
  className,
}: {
  children: React.ReactNode;
  speed?: number;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const reduce = useReducedMotion();
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start end", "end start"],
  });
  const y = useTransform(scrollYProgress, [0, 1], ["0%", `${speed * 100}%`]);
  return (
    <div ref={ref} className={className}>
      <motion.div style={{ y: reduce ? 0 : y }}>{children}</motion.div>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* <MagneticButton> — cursor-attracting button. Desktop only; disabled on     */
/* reduced motion. Style the inner element yourself.                          */
/* -------------------------------------------------------------------------- */
export function MagneticButton({
  children,
  strength = 0.3,
  className,
  ...props
}: React.ComponentProps<typeof motion.button> & { strength?: number }) {
  const ref = useRef<HTMLButtonElement>(null);
  const reduce = useReducedMotion();

  function handleMove(e: React.MouseEvent<HTMLButtonElement>) {
    if (reduce || !ref.current) return;
    const rect = ref.current.getBoundingClientRect();
    const x = (e.clientX - rect.left - rect.width / 2) * strength;
    const y = (e.clientY - rect.top - rect.height / 2) * strength;
    ref.current.style.transform = `translate(${x}px, ${y}px)`;
  }
  function reset() {
    if (ref.current) ref.current.style.transform = "translate(0px, 0px)";
  }

  return (
    <motion.button
      ref={ref}
      onMouseMove={handleMove}
      onMouseLeave={reset}
      transition={spring.snappy}
      className={className}
      {...props}
    >
      {children}
    </motion.button>
  );
}
