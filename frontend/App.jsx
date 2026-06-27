"use client";
import React from 'react';
import GradientText from './components/GradientText';
import SplashCursor from './components/SplashCursor';
import ScrollReveal from './components/ScrollReveal';

export default function App() {
  return (
    <div style={{ padding: 40, background: '#060010', minHeight: '100vh' }}>
      <GradientText
        colors={["#ffffff", "#518ea9", "#1e3885"]}
        animationSpeed={2.5}
        showBorder={false}
        className="custom-class"
      >
        Add a splash of color!
      </GradientText>

      <ScrollReveal
        baseOpacity={0.1}
        enableBlur
        baseRotation={3}
        blurStrength={4}
      >
        When does a man die? When he is hit by a bullet? No! When he suffers a disease?
        No! When he ate a soup made out of a poisonous mushroom?
        No! A man dies when he is forgotten!
      </ScrollReveal>

      {/* Mount the SplashCursor so the fluid effect runs across the page */}
      <SplashCursor />
    </div>
  );
}
        } catch (e) {
