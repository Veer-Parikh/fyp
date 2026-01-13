"use client"

import type React from "react"

import { Navbar } from "@/components/navbar"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { AlertCircle, TrendingUp, Activity } from "lucide-react"

export default function IDSPage() {
  return (
    <>
      <main className="min-h-screen bg-background">
        {/* Background grid */}
        <div className="fixed inset-0 opacity-5 pointer-events-none">
          <div
            className="absolute inset-0"
            style={{
              backgroundImage:
                "linear-gradient(0deg, rgba(0,255,150,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(0,255,150,0.1) 1px, transparent 1px)",
              backgroundSize: "50px 50px",
            }}
          ></div>
        </div>

        <section className="relative max-w-7xl mx-auto px-6 py-24">
          {/* Hero Section */}
          <div className="mb-16">
            <h1 className="text-4xl md:text-5xl font-bold font-mono mb-4">
              <span className="cyber-gradient-text">Intrusion Detection</span>
              <br />
              System
            </h1>
            <p className="text-lg text-muted-foreground max-w-2xl">
              Real-time threat detection, analysis, and XAI-powered explanations
            </p>
          </div>

          {/* Coming Soon Card */}
          <div className="mb-12 p-8 rounded-xl bg-card/50 border-2 glow-border space-y-4">
            <div className="flex items-center gap-3">
              <AlertCircle className="w-6 h-6 text-accent animate-pulse" />
              <h2 className="text-2xl font-mono font-semibold">Coming Soon</h2>
            </div>
            <p className="text-foreground leading-relaxed">
              The IDS module is under active development. This page will feature real-time intrusion detection with XAI
              explanations, NLP-based attack classification, and live threat monitoring.
            </p>
          </div>

          {/* Placeholder Cards Grid */}
          <div className="grid md:grid-cols-3 gap-6">
            <PlaceholderCard
              title="Real-time Detection"
              description="Live threat detection with instant alerts"
              icon={<Activity className="w-8 h-8" />}
            />
            <PlaceholderCard
              title="XAI Explanations"
              description="Understand why threats were detected"
              icon={<AlertCircle className="w-8 h-8" />}
            />
            <PlaceholderCard
              title="Attack Classification"
              description="NLP-based threat categorization"
              icon={<TrendingUp className="w-8 h-8" />}
            />
          </div>

          {/* Feature Preview */}
          <div className="mt-16 p-8 rounded-xl bg-background/50 border border-border/50 terminal-box space-y-4">
            <h3 className="font-mono font-semibold text-accent glow-text mb-4">Upcoming Features</h3>
            <ul className="space-y-2 font-mono text-sm">
              <li className="text-muted-foreground">
                {"> "}
                <span className="text-accent">Live threat feeds</span>
              </li>
              <li className="text-muted-foreground">
                {"> "}
                <span className="text-accent">Behavioral analysis</span>
              </li>
              <li className="text-muted-foreground">
                {"> "}
                <span className="text-accent">Anomaly detection</span>
              </li>
              <li className="text-muted-foreground">
                {"> "}
                <span className="text-accent">Alert correlations</span>
              </li>
              <li className="text-muted-foreground">
                {"> "}
                <span className="text-accent">Automated response</span>
              </li>
            </ul>
          </div>
        </section>
      </main>
    </>
  )
}

function PlaceholderCard({ title, description, icon }: { title: string; description: string; icon: React.ReactNode }) {
  return (
    <Card className="bg-card/50 border-accent/20 hover:border-accent/50 transition-all duration-300 glow-border">
      <CardHeader>
        <div className="text-accent mb-3">{icon}</div>
        <CardTitle className="font-mono text-lg">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <CardDescription className="text-muted-foreground">{description}</CardDescription>
      </CardContent>
    </Card>
  )
}
// "use client"

// import { useState, ReactNode } from "react"

// import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
// import { Button } from "@/components/ui/button"
// import { Input } from "@/components/ui/input"

// import { Activity, Brain } from "lucide-react"

// /* ---------- Types ---------- */
// type XAIItem = {
//   feature: string
//   impact: number
// }

// type PredictionResult = {
//   prediction: string
//   confidence: number
//   explanation: XAIItem[]
// }

// export default function IDSPage() {
//   const [features, setFeatures] = useState<number[]>(Array(7).fill(0))
//   const [loading, setLoading] = useState(false)
//   const [result, setResult] = useState<PredictionResult | null>(null)

//   const handleChange = (index: number, value: string) => {
//     const updated = [...features]
//     updated[index] = Number(value)
//     setFeatures(updated)
//   }

//   const analyzeTraffic = async () => {
//     setLoading(true)
//     setResult(null)

//     try {
//       const res = await fetch("http://localhost:9000/predict", {
//         method: "POST",
//         headers: {
//           "Content-Type": "application/json",
//         },
//         body: JSON.stringify({
//           features: features, // ✅ FIXED
//         }),
//       })

//       if (!res.ok) {
//         throw new Error("Backend error")
//       }

//       const data: PredictionResult = await res.json()
//       setResult(data)
//     } catch (err) {
//       console.error(err)
//       setResult(null)
//     } finally {
//       setLoading(false)
//     }
//   }

//   return (
//     <main className="min-h-screen bg-background">
//       <section className="relative max-w-7xl mx-auto px-6 py-24 space-y-16">

//         {/* Header */}
//         <div>
//           <h1 className="text-4xl font-bold font-mono mb-4">
//             Intrusion Detection System
//           </h1>
//           <p className="text-lg text-muted-foreground">
//             Real-time threat detection with Explainable AI
//           </p>
//         </div>

//         <div className="grid md:grid-cols-2 gap-8">

//           {/* INPUT */}
//           <Card className="bg-card/50">
//             <CardHeader>
//               <CardTitle className="font-mono flex items-center gap-2">
//                 <Activity className="text-accent" />
//                 Traffic Input
//               </CardTitle>
//               <CardDescription>
//                 Enter PCA-transformed network features
//               </CardDescription>
//             </CardHeader>

//             <CardContent className="space-y-4">
//               {features.map((_, i) => (
//                 <Input
//                   key={i}
//                   type="number"
//                   placeholder={`Principal Component ${i + 1}`}
//                   onChange={(e) => handleChange(i, e.target.value)}
//                 />
//               ))}

//               <Button
//                 className="w-full mt-4"
//                 onClick={analyzeTraffic}
//                 disabled={loading}
//               >
//                 {loading ? "Analyzing..." : "Analyze Traffic"}
//               </Button>
//             </CardContent>
//           </Card>

//           {/* OUTPUT */}
//           <Card className="bg-card/50">
//             <CardHeader>
//               <CardTitle className="font-mono flex items-center gap-2">
//                 <Brain className="text-accent" />
//                 Model Output & XAI
//               </CardTitle>
//               <CardDescription>
//                 Prediction, confidence, and explanation
//               </CardDescription>
//             </CardHeader>

//             <CardContent>
//               {!result ? (
//                 <p className="text-muted-foreground text-sm">
//                   Awaiting analysis input...
//                 </p>
//               ) : (
//                 <div className="space-y-6">

//                   {/* Prediction */}
//                   <div>
//                     <p className="font-mono text-accent">{"> Prediction"}</p>
//                     <p className="text-lg font-semibold">
//                       {result.prediction}
//                     </p>
//                     <p className="text-sm text-muted-foreground">
//                       Confidence: {(result.confidence * 100).toFixed(2)}%
//                     </p>
//                   </div>

//                   {/* XAI */}
//                   <div>
//                     <p className="font-mono text-accent mb-2">
//                       {"> XAI Feature Importance"}
//                     </p>

//                     <div className="space-y-2">
//                       {result.explanation.map((f, idx) => (
//                         <div key={idx}>
//                           <div className="flex justify-between text-sm">
//                             <span>{f.feature}</span>
//                             <span>{(Math.abs(f.impact) * 100).toFixed(1)}%</span>
//                           </div>
//                           <div className="h-2 bg-muted rounded">
//                             <div
//                               className="h-2 bg-accent rounded"
//                               style={{ width: `${Math.abs(f.impact) * 100}%` }}
//                             />
//                           </div>
//                         </div>
//                       ))}
//                     </div>
//                   </div>

//                 </div>
//               )}
//             </CardContent>
//           </Card>

//         </div>
//       </section>
//     </main>
//   )
// }
