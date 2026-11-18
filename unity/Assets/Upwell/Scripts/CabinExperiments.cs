using System;
using UnityEngine;

namespace Upwell {
    // The proof mass and primer both ring down under passive spring/damper forces.
    // The exact underdamped solution also behaves at a stalled browser frame rate.
    public struct SpringReading {
        public float value, velocity;

        public void Follow(float target, float frequency, float damping, float dt) {
            if (dt <= 0) return;
            float decay = damping * frequency;
            float wd = frequency * Mathf.Sqrt(1 - damping * damping);
            float angle = wd * dt;
            float cosine = Mathf.Cos(angle), sine = Mathf.Sin(angle);
            float displacement = value - target;
            float envelope = Mathf.Exp(-decay * dt);
            value = target + envelope * (displacement * cosine + (velocity + decay * displacement) * sine / wd);
            velocity = envelope * (velocity * cosine - (decay * velocity + frequency * frequency * displacement) * sine / wd);
        }
    }

    [DefaultExecutionOrder(34)]
    public sealed class CabinExperiments : MonoBehaviour {
        public TransitRide ride;
        public Transform proofMass, upperSpring, lowerSpring;
        public ProofSpring upperWire,lowerWire;
        public CapillaryCell fluid;
        public Light scaleLamp;
        public float metresPerG = .162f, referenceG = 1, upperLength, lowerLength;
        public Vector3 upperFixed, lowerFixed, upperMoving, lowerMoving;
        public float SignedG { get; private set; }
        public float IndicatedG => needle.value;
        public float Preload => .10f * inputSpring.value;
        public bool Testing => inputSpring.value > .04f;
        public int TestCount { get; private set; }
        public int PrimeCount { get; private set; }
        SpringReading needle, inputSpring, primerSpring;
        Vector3 homeMass;
        bool ready, testHold;
        float pulseRemaining, primeRemaining;
        double lastRouteTime = -1000;

        void Initialize() {
            if (ready || !proofMass || !fluid) return;
            ready = true;
            homeMass = proofMass.localPosition;
            needle.value = referenceG;
        }

        public bool IsInstrument(string id) =>
            id == "accelerometer" || id == "accel_test" || id == "capillary_cell" || id == "capillary_primer" || FractureCartridge.IsInstrument(id);

        public string Status(string id) {
            if(FractureCartridge.IsInstrument(id)&&ride.fracture)return ride.fracture.Status;
            if (id == "accelerometer" || id == "accel_test")
                return (Testing ? "Calibration load applied" : "Vertical proof mass") + "  ·  " + IndicatedG.ToString("+0.000;-0.000;0.000") + " g";
            if (id == "capillary_cell" || id == "capillary_primer")
                return fluid.Moving ? "Primer pulse · interface settling" :
                    fluid.Bond < .7f ? "Surface tension holds the gas pocket" :
                    fluid.Bond < 10 ? "Capillary and apparent-weight forces share the interface" :
                    SignedG < 0 ? "Braking · gas against the lower wall" : "Gas above the liquid reservoir";
            return null;
        }

        public bool HoldControl(TransitProp prop) {
            if(prop&&prop.id=="fracture_press"&&ride.fracture){ride.fracture.BeginPress();return true;}
            if (!prop || prop.id != "accel_test" && prop.id != "capillary_primer") return false;
            if (prop.id == "accel_test") {
                testHold = true;
                TestCount++;
            } else Prime();
            ride.Click(ride.relay, .52f);
            return true;
        }

        public void ReleaseControl(TransitProp prop) {
            if (!prop) return;
            if(prop.id=="fracture_press"&&ride.fracture)ride.fracture.ReleasePress();
            if (prop.id == "accel_test") testHold = false;
        }

        public void Test() {
            TestCount++;
            pulseRemaining = .38f;
            ride.Click(ride.relay, .57f);
        }

        public void Prime() {
            if (primeRemaining > 0 || primerSpring.value > .56f) return;
            PrimeCount++;
            primeRemaining = .19f;
            fluid.Prime();
            ride.Click(ride.runner, .47f);
        }

        public void Operate(string id) {
            if (id == "accelerometer" || id == "accel_test") Test();
            else Prime();
        }

        public void Advance(float dt) {
            Initialize();
            if (!ready) return;
            if(scaleLamp&&ride.systems)scaleLamp.intensity=.26f+1.37f*ride.systems.GainValue;
            var acceleration = ride.Forces.Apparent - ride.StructureImpulse;
            SignedG = -acceleration.y / 9.80665f;
            if (Math.Abs(ride.Seconds - lastRouteTime) > 1.6) {
                needle = new SpringReading { value = SignedG };inputSpring = primerSpring = new SpringReading();
                pulseRemaining = primeRemaining = 0;testHold = false;fluid.Rebase(acceleration);
            }
            lastRouteTime = ride.Seconds;
            float remaining = Mathf.Min(dt, 1.5f);
            while (remaining > .00001f) {
                float step = Mathf.Min(remaining, 1 / 90f);
                inputSpring.Follow(testHold || pulseRemaining > 0 ? 1 : 0, 32, .76f, step);
                primerSpring.Follow(primeRemaining > 0 ? 1 : 0, 30, .75f, step);
                inputSpring.value = Mathf.Clamp01(inputSpring.value);
                primerSpring.value = Mathf.Clamp01(primerSpring.value);
                needle.Follow(Mathf.Clamp(SignedG + Preload, -.18f, 1.18f),
                    Mathf.Sqrt(9.80665f / metresPerG), .38f, step);
                needle.value = Mathf.Clamp(needle.value, -.18f, 1.18f);
                pulseRemaining = Mathf.Max(0, pulseRemaining - step);
                primeRemaining = Mathf.Max(0, primeRemaining - step);
                fluid.Advance(acceleration, step);
                remaining -= step;
            }
            float offset = (referenceG - needle.value) * metresPerG;
            proofMass.localPosition = homeMass + Vector3.up * offset;
            if (ride.props.TryGetValue("accel_test",out var testButton)) testButton.Drive(inputSpring.value);
            if (ride.props.TryGetValue("capillary_primer",out var bulb)) bulb.Drive(primerSpring.value);
            if (upperWire) upperWire.Length(Mathf.Max(.005f,upperFixed.y-upperMoving.y-offset));
            if (lowerWire) lowerWire.Length(Mathf.Max(.005f,lowerMoving.y+offset-lowerFixed.y));
            fluid.Publish();
        }

        void Update() => Advance(Time.unscaledDeltaTime);
    }
}
