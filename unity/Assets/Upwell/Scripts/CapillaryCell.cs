using System;
using UnityEngine;

namespace Upwell {
    public sealed class CapillaryCell : MonoBehaviour {
        public Renderer volume;
        public Vector3 center, right = Vector3.back, up = Vector3.up, front = Vector3.left;
        public float radius = .102f, depth = .022f;
        public const float GasFraction = .23f;
        const float Density = 997, Tension = .072f;
        public float Bond { get; private set; }
        public Vector2 GasCenter { get; private set; }
        public float GasRadius { get; private set; }
        public float Slosh => interfaceMotion.value;
        public bool Moving => Mathf.Abs(interfaceMotion.value) + Mathf.Abs(interfaceMotion.velocity) * .22f > .015f;
        SpringReading interfaceMotion, buoyantRight, buoyantUp;
        const int Sections = 9;
        readonly float[] radii = new float[Sections], fractions = new float[Sections];
        float lastDistance = -1, coreRadius, coreDepth;
        MaterialPropertyBlock properties;

        public static double IntersectionArea(double d, double radius) {
            if (radius <= 0 || d >= 1 + radius) return 0;
            if (d <= Math.Abs(1 - radius)) return Math.PI * Math.Min(1, radius * radius);
            double a = (d * d + 1 - radius * radius) / (2 * d);
            double b = (d * d + radius * radius - 1) / (2 * d * radius);
            double cross = Math.Max(0, (-d + 1 + radius) * (d + 1 - radius) * (d - 1 + radius) * (d + 1 + radius));
            return Math.Acos(Math.Max(-1, Math.Min(1, a))) +
                radius * radius * Math.Acos(Math.Max(-1, Math.Min(1, b))) - .5 * Math.Sqrt(cross);
        }

        static float RadiusForArea(float d, float fraction) {
            if (d + Mathf.Sqrt(fraction) <= 1) return Mathf.Sqrt(fraction);
            double low = Math.Max(0, d - 1), high = d + 1, target = Math.PI * fraction;
            for (int i = 0; i < 25; i++) {
                double probe = (low + high) * .5;
                if (IntersectionArea(d, probe) < target) low = probe; else high = probe;
            }
            return (float)((low + high) * .5);
        }

        public void Prime() {
            interfaceMotion.velocity = Mathf.Clamp(interfaceMotion.velocity + 1.4f, -1.8f, 1.8f);
        }

        public void Rebase(Vector3 acceleration) {
            buoyantRight = new SpringReading { value = -Vector3.Dot(acceleration, right) };
            buoyantUp = new SpringReading { value = -Vector3.Dot(acceleration, up) };
            interfaceMotion = new SpringReading();
        }

        public void Advance(Vector3 apparatusAcceleration, float dt) {
            Vector2 outward = -new Vector2(Vector3.Dot(apparatusAcceleration, right), Vector3.Dot(apparatusAcceleration, up));
            float acceleration = outward.magnitude;
            float k = 1.84f / radius;
            float frequency = Mathf.Sqrt(k * acceleration + Tension / Density * k * k * k + 2.25f);
            float damping = .33f + .27f * Mathf.Exp(-acceleration / .19f);
            buoyantRight.Follow(outward.x, frequency, damping, dt);
            buoyantUp.Follow(outward.y, frequency, damping, dt);
            interfaceMotion.Follow(0, frequency, damping, dt);
            if (Mathf.Abs(interfaceMotion.value) > .29f) {
                interfaceMotion.value = Mathf.Clamp(interfaceMotion.value, -.29f, .29f);
                if (Mathf.Sign(interfaceMotion.velocity) == Mathf.Sign(interfaceMotion.value)) interfaceMotion.velocity *= -.08f;
            }
            var buoyancy = new Vector2(buoyantRight.value, buoyantUp.value);
            Bond = Density * radius * radius * buoyancy.magnitude / Tension;
            if (buoyancy.sqrMagnitude > 1e-16f) buoyancy /= buoyancy.magnitude;
            float q = interfaceMotion.value, sine = Mathf.Sin(q), cosine = Mathf.Cos(q);
            Vector2 rotary = new Vector2(buoyancy.x * cosine - buoyancy.y * sine, buoyancy.x * sine + buoyancy.y * cosine);
            GasCenter = new Vector2(.08f, .035f) + rotary * (28 * (1 - Mathf.Exp(-Bond / 85))) + q * new Vector2(.75f, .16f);
        }

        public void Publish() {
            if (!volume) return;
            if (properties == null) {
                properties = new MaterialPropertyBlock();
                coreRadius = 1 - .00025f / radius;
                coreDepth = 1 - 2 * .00016f / depth;
                float total = 0;
                for (int i = 0; i < Sections; i++) {
                    float z = 2f * i / (Sections - 1) - 1;
                    float shoulder=Mathf.Min(.30f,.82f*depth/(2*radius*Mathf.Sqrt(GasFraction)));
                    float radiusRatio=1-shoulder*(1-Mathf.Sqrt(Mathf.Max(0,1-z*z)));
                    fractions[i]=radiusRatio*radiusRatio;
                    total += fractions[i] * (i == 0 || i == Sections - 1 ? .5f : 1);
                }
                for (int i = 0; i < Sections; i++) fractions[i] *= GasFraction * (Sections - 1) / (total * coreRadius * coreRadius * coreDepth);
            }
            float d = GasCenter.magnitude;
            if (Mathf.Abs(d - lastDistance) > .000001f) {
                lastDistance = d;
                for (int i = 0; i < Sections; i++) radii[i] = RadiusForArea(d, fractions[i]);
                GasRadius = radii[Sections/2];
            }
            properties.SetVector("_CellCenter", center);
            properties.SetVector("_CellRight", right);
            properties.SetVector("_CellUp", up);
            properties.SetVector("_CellFront", front);
            properties.SetVector("_Chamber", new Vector4(radius, depth, coreRadius, coreDepth));
            properties.SetFloatArray("_Radii",radii);
            properties.SetVector("_GasCenter", new Vector4(GasCenter.x, GasCenter.y, 0, 0));
            volume.SetPropertyBlock(properties);
        }

        public float MeasuredGasFraction {
            get {
                double total = 0;
                for (int i = 0; i < Sections; i++) total += (i == 0 || i == Sections - 1 ? .5 : 1) * IntersectionArea(lastDistance,radii[i]);
                return (float)(total * coreRadius * coreRadius * coreDepth / (Math.PI * (Sections - 1)));
            }
        }
    }
}
