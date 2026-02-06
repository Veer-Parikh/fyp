"use client"

import { useState } from "react"
import { Loader } from "@/components/loader"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Upload, Brain, Play } from "lucide-react"

type PredictionResult = {
  prediction?: number
  label?: string
  confidence?: number
}

export default function IDSPage() {
  const [features, setFeatures] = useState<number[]>([])
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<PredictionResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  /* ---------------- CSV UPLOAD ---------------- */
  const handleCSVUpload = async (e: any) => {
    const file = e.target.files[0]
    if (!file) return

    try {
      const text = await file.text()
      const rows = text.trim().split("\n")

      if (rows.length === 0) {
        setError("CSV is empty")
        return
      }

      const values = rows[0].split(",")

      const nums = values
        .map((v: string) => Number(v.trim()))
        .filter((v: number) => !isNaN(v))

      if (nums.length !== 52) {
        setError(`CSV must contain exactly 52 features. Found ${nums.length}`)
        return
      }

      setFeatures(nums)
      setError(null)
      setResult(null)
    } catch {
      setError("Failed to read CSV")
    }
  }

  /* ---------------- RUN IDS ---------------- */
  const runIDS = async () => {
    if (features.length !== 52) {
      setError("Upload valid CSV with 52 features first")
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const res = await fetch("https://ids-dnn.onrender.com/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ features }),
      })

      const data = await res.json()

      if (!res.ok) throw new Error(data?.error || "Prediction failed")

      setResult(data)
    } catch (err: any) {
      setError(err.message || "Server error")
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-background">

      {/* GRID BACKGROUND */}
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

      <section className="relative max-w-7xl mx-auto px-6 py-12">

        {/* HEADER */}
        <div className="mb-12">
          <h1 className="text-4xl md:text-5xl font-bold font-mono mb-4">
            <span className="cyber-gradient-text">Intrusion</span>
            <br />
            Detection System
          </h1>
          <p className="text-muted-foreground">
            Upload CICIDS feature CSV and detect real-time network attacks using deep learning
          </p>
        </div>

        {/* MAIN CARD */}
        <Card className="mb-12 bg-card/50 border-accent/20 glow-border">
          <CardHeader>
            <CardTitle className="font-mono">IDS Configuration</CardTitle>
            <CardDescription>Upload CICIDS feature CSV (52 features)</CardDescription>
          </CardHeader>

          <CardContent className="space-y-6">

            {/* CSV UPLOAD */}
            <div className="space-y-2">
              <label className="block text-sm font-mono text-foreground">
                Upload Feature CSV
              </label>

              <input
                type="file"
                accept=".csv"
                onChange={handleCSVUpload}
                disabled={loading}
                className="w-full px-4 py-3 rounded-lg bg-background/50 border border-border/50 focus:border-accent/50 text-foreground focus:outline-none transition-colors font-mono text-sm"
              />
            </div>

            {/* ERROR */}
            {error && (
              <div className="p-4 rounded-lg bg-red-400/10 border border-red-400/30">
                <p className="text-sm text-red-400 font-mono">{error}</p>
              </div>
            )}

            {/* RUN BUTTON */}
            <button
              onClick={runIDS}
              disabled={loading || features.length !== 52}
              className="w-full cyber-button flex items-center justify-center gap-2 px-6 py-3 bg-accent/20 hover:bg-accent/40 text-accent border border-accent/50 rounded-lg font-mono font-semibold transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Play className="w-4 h-4" />
              {loading ? "Analyzing Traffic..." : "Run IDS Detection"}
            </button>
          </CardContent>
        </Card>

        {/* LOADER */}
        {loading && (
          <div className="mb-12">
            <Card className="bg-card/50 border-accent/20">
              <CardContent className="py-12">
                <Loader />
              </CardContent>
            </Card>
          </div>
        )}

        {/* RESULT */}
        {result && !loading && (
          <div className="space-y-10 mt-10">
            <h2 className="text-3xl font-bold font-mono">Detection Result</h2>

            <Card className="border-accent/40 bg-card/50">
              <CardHeader>
                <CardTitle className="font-mono flex items-center gap-2">
                  <Brain className="text-accent" />
                  AI Prediction
                </CardTitle>
                <CardDescription>Deep learning intrusion detection output</CardDescription>
              </CardHeader>

              <CardContent className="space-y-4 font-mono">
                <p className="text-lg">
                  Prediction:{" "}
                  <span
                    className={
                      result.label === "Attack"
                        ? "text-red-400 font-bold"
                        : "text-green-400 font-bold"
                    }
                  >
                    {result.label || result.prediction}
                  </span>
                </p>

                {result.confidence !== undefined && (
                  <p className="text-sm text-muted-foreground">
                    Confidence: {(result.confidence * 100).toFixed(4)}%
                  </p>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {/* PLACEHOLDER */}
        {!loading && !result && !error && (
          <Card className="bg-card/50 border-border/50">
            <CardContent className="py-12 text-center">
              <p className="text-muted-foreground font-mono">
                Upload a CICIDS CSV and click "Run IDS Detection" to analyze network traffic
              </p>
            </CardContent>
          </Card>
        )}

      </section>
    </main>
  )
}



// "use client"

// import { useState } from "react"
// import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
// import { Button } from "@/components/ui/button"
// import { Upload, AlertCircle, Brain } from "lucide-react"

// type PredictionResult = {
//   prediction?: number
//   label?: string
//   confidence?: number
// }

// export default function IDSPage() {
//   const [features, setFeatures] = useState<number[]>([])
//   const [loading, setLoading] = useState(false)
//   const [result, setResult] = useState<PredictionResult | null>(null)
//   const [error, setError] = useState<string | null>(null)

//   /* ---------------- CSV UPLOAD ---------------- */
//   const handleCSVUpload = async (e: any) => {
//     const file = e.target.files[0]
//     if (!file) return

//     try {
//       const text = await file.text()
//       const rows = text.trim().split("\n")

//       if (rows.length === 0) {
//         setError("CSV is empty")
//         return
//       }

//       // take first row only
//       const values = rows[0].split(",")

//       const nums = values
//         .map((v: string) => Number((v as string).trim()))
//         .filter((v: number) => !isNaN(v))

//       if (nums.length !== 52) {
//         setError(`CSV must contain exactly 52 features. Found ${nums.length}`)
//         return
//       }

//       setFeatures(nums)
//       setError(null)
//       setResult(null)

//       console.log("Parsed features:", nums)
//     } catch (err) {
//       console.error(err)
//       setError("Failed to read CSV")
//     }
//   }

//   /* ---------------- CALL IDS MODEL ---------------- */
//   const runIDS = async () => {
//     if (features.length !== 52) {
//       setError("Upload valid CSV with 52 features first")
//       return
//     }

//     setLoading(true)
//     setError(null)
//     setResult(null)

//     try {
//       const res = await fetch("https://ids-dnn.onrender.com/predict", {
//         method: "POST",
//         headers: {
//           "Content-Type": "application/json",
//         },
//         body: JSON.stringify({
//           features: features,
//         }),
//       })

//       const data = await res.json()

//       if (!res.ok) {
//         throw new Error(data?.error || "Prediction failed")
//       }

//       setResult(data)
//     } catch (err: any) {
//       console.error(err)
//       setError(err.message || "Server error")
//     } finally {
//       setLoading(false)
//     }
//   }

//   /* ---------------- UI ---------------- */
//   return (
//     <main className="min-h-screen bg-background">
//       <section className="max-w-5xl mx-auto px-6 py-24 space-y-10">

//         {/* HEADER */}
//         <div>
//           <h1 className="text-4xl font-bold font-mono mb-3">
//             Intrusion Detection System
//           </h1>
//           <p className="text-muted-foreground">
//             Upload CICIDS feature CSV → AI detects network attack
//           </p>
//         </div>

//         {/* UPLOAD CARD */}
//         <Card className="bg-card/50 border-accent/30">
//           <CardHeader>
//             <CardTitle className="flex items-center gap-2 font-mono">
//               <Upload className="text-accent" />
//               Upload CSV
//             </CardTitle>
//             <CardDescription>
//               CSV must contain exactly 52 feature values (single row)
//             </CardDescription>
//           </CardHeader>

//           <CardContent className="space-y-4">
//             <input
//               type="file"
//               accept=".csv"
//               onChange={handleCSVUpload}
//               className="block w-full text-sm"
//             />

//             <Button
//               onClick={runIDS}
//               disabled={loading}
//               className="w-full"
//             >
//               {loading ? "Analyzing Traffic..." : "Run IDS Detection"}
//             </Button>

//             {error && (
//               <div className="flex gap-2 text-red-400 text-sm mt-2">
//                 <AlertCircle size={18} />
//                 {error}
//               </div>
//             )}
//           </CardContent>
//         </Card>

//         {/* RESULT */}
//         {result && (
//           <Card className="bg-card/50 border-green-500/40">
//             <CardHeader>
//               <CardTitle className="flex items-center gap-2 font-mono">
//                 <Brain className="text-green-400" />
//                 Detection Result
//               </CardTitle>
//             </CardHeader>

//             <CardContent className="space-y-3">
//               <p className="text-lg font-semibold">
//                 Prediction:{" "}
//                 <span
//                   className={
//                     result.label === "Attack"
//                       ? "text-red-400"
//                       : "text-green-400"
//                   }
//                 >
//                   {result.label || result.prediction}
//                 </span>
//               </p>

//               {result.confidence !== undefined && (
//                 <p className="text-sm text-muted-foreground">
//                   Confidence: {(result.confidence * 100).toFixed(4)}%
//                 </p>
//               )}
//             </CardContent>
//           </Card>
//         )}

//       </section>
//     </main>
//   )
// }


// // "use client"

// // import { useState } from "react"
// // import Papa from "papaparse"

// // import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
// // import { Button } from "@/components/ui/button"
// // import { AlertCircle, Upload, Brain } from "lucide-react"

// // type PredictionResult = {
// //   prediction: number
// //   label: string
// //   confidence: number
// // }

// // export default function IDSPage() {
// //   const [loading, setLoading] = useState(false)
// //   const [result, setResult] = useState<PredictionResult | null>(null)
// //   const [error, setError] = useState<string | null>(null)
// //   const [features, setFeatures] = useState<number[]>([])

// //   /* ---------------- CSV UPLOAD ---------------- */
// //   const handleCSVUpload = (e: any) => {
// //     const file = e.target.files[0]
// //     if (!file) return

// //     Papa.parse(file, {
// //       complete: (res) => {
// //         try {
// //           let row = res.data[0]

// //           if (!row || row.length === 0) {
// //             setError("CSV empty")
// //             return
// //           }

// //           // convert to numbers
// //           const nums = row.map((v: any) => Number(v)).filter((v: any) => !isNaN(v))

// //           if (nums.length !== 52) {
// //             setError(`CSV must contain exactly 52 features. Found ${nums.length}`)
// //             return
// //           }

// //           setFeatures(nums)
// //           setError(null)
// //         } catch (err) {
// //           setError("CSV parsing failed")
// //         }
// //       },
// //     })
// //   }

// //   /* ---------------- CALL MODEL ---------------- */
// //   const analyze = async () => {
// //     if (features.length !== 52) {
// //       setError("Upload valid CSV first")
// //       return
// //     }

// //     setLoading(true)
// //     setError(null)
// //     setResult(null)

// //     try {
// //       const res = await fetch("https://ids-dnn.onrender.com/predict", {
// //         method: "POST",
// //         headers: {
// //           "Content-Type": "application/json",
// //         },
// //         body: JSON.stringify({
// //           features: features,
// //         }),
// //       })

// //       const data = await res.json()

// //       if (!res.ok) {
// //         throw new Error(data.error || "Prediction failed")
// //       }

// //       setResult(data)
// //     } catch (err: any) {
// //       setError(err.message)
// //     } finally {
// //       setLoading(false)
// //     }
// //   }

// //   /* ---------------- UI ---------------- */
// //   return (
// //     <main className="min-h-screen bg-background">
// //       <section className="max-w-5xl mx-auto px-6 py-24 space-y-10">

// //         <div>
// //           <h1 className="text-4xl font-bold font-mono mb-3">
// //             Intrusion Detection System
// //           </h1>
// //           <p className="text-muted-foreground">
// //             Upload CICIDS feature CSV → AI detects attack
// //           </p>
// //         </div>

// //         {/* UPLOAD CARD */}
// //         <Card className="bg-card/50 border-accent/30">
// //           <CardHeader>
// //             <CardTitle className="flex items-center gap-2 font-mono">
// //               <Upload className="text-accent" />
// //               Upload CSV Features
// //             </CardTitle>
// //             <CardDescription>
// //               CSV must contain exactly 52 feature values (single row)
// //             </CardDescription>
// //           </CardHeader>

// //           <CardContent className="space-y-4">
// //             <input
// //               type="file"
// //               accept=".csv"
// //               onChange={handleCSVUpload}
// //               className="block w-full text-sm"
// //             />

// //             <Button
// //               onClick={analyze}
// //               disabled={loading}
// //               className="w-full"
// //             >
// //               {loading ? "Analyzing..." : "Run IDS Detection"}
// //             </Button>

// //             {error && (
// //               <div className="flex gap-2 text-red-400 text-sm">
// //                 <AlertCircle size={18} /> {error}
// //               </div>
// //             )}
// //           </CardContent>
// //         </Card>

// //         {/* RESULT */}
// //         {result && (
// //           <Card className="bg-card/50 border-green-500/40">
// //             <CardHeader>
// //               <CardTitle className="flex items-center gap-2 font-mono">
// //                 <Brain className="text-green-400" />
// //                 Detection Result
// //               </CardTitle>
// //             </CardHeader>

// //             <CardContent className="space-y-3">
// //               <p className="text-lg font-semibold">
// //                 Prediction:{" "}
// //                 <span className={result.label === "Attack" ? "text-red-400" : "text-green-400"}>
// //                   {result.label}
// //                 </span>
// //               </p>

// //               <p className="text-sm text-muted-foreground">
// //                 Confidence: {(result.confidence * 100).toFixed(4)}%
// //               </p>
// //             </CardContent>
// //           </Card>
// //         )}

// //       </section>
// //     </main>
// //   )
// // }


// // // "use client"

// // // import type React from "react"

// // // import { Navbar } from "@/components/navbar"
// // // import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
// // // import { AlertCircle, TrendingUp, Activity } from "lucide-react"

// // // export default function IDSPage() {
// // //   return (
// // //     <>
// // //       <main className="min-h-screen bg-background">
// // //         {/* Background grid */}
// // //         <div className="fixed inset-0 opacity-5 pointer-events-none">
// // //           <div
// // //             className="absolute inset-0"
// // //             style={{
// // //               backgroundImage:
// // //                 "linear-gradient(0deg, rgba(0,255,150,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(0,255,150,0.1) 1px, transparent 1px)",
// // //               backgroundSize: "50px 50px",
// // //             }}
// // //           ></div>
// // //         </div>

// // //         <section className="relative max-w-7xl mx-auto px-6 py-24">
// // //           {/* Hero Section */}
// // //           <div className="mb-16">
// // //             <h1 className="text-4xl md:text-5xl font-bold font-mono mb-4">
// // //               <span className="cyber-gradient-text">Intrusion Detection</span>
// // //               <br />
// // //               System
// // //             </h1>
// // //             <p className="text-lg text-muted-foreground max-w-2xl">
// // //               Real-time threat detection, analysis, and XAI-powered explanations
// // //             </p>
// // //           </div>

// // //           {/* Coming Soon Card */}
// // //           <div className="mb-12 p-8 rounded-xl bg-card/50 border-2 glow-border space-y-4">
// // //             <div className="flex items-center gap-3">
// // //               <AlertCircle className="w-6 h-6 text-accent animate-pulse" />
// // //               <h2 className="text-2xl font-mono font-semibold">Coming Soon</h2>
// // //             </div>
// // //             <p className="text-foreground leading-relaxed">
// // //               The IDS module is under active development. This page will feature real-time intrusion detection with XAI
// // //               explanations, NLP-based attack classification, and live threat monitoring.
// // //             </p>
// // //           </div>

// // //           {/* Placeholder Cards Grid */}
// // //           <div className="grid md:grid-cols-3 gap-6">
// // //             <PlaceholderCard
// // //               title="Real-time Detection"
// // //               description="Live threat detection with instant alerts"
// // //               icon={<Activity className="w-8 h-8" />}
// // //             />
// // //             <PlaceholderCard
// // //               title="XAI Explanations"
// // //               description="Understand why threats were detected"
// // //               icon={<AlertCircle className="w-8 h-8" />}
// // //             />
// // //             <PlaceholderCard
// // //               title="Attack Classification"
// // //               description="NLP-based threat categorization"
// // //               icon={<TrendingUp className="w-8 h-8" />}
// // //             />
// // //           </div>

// // //           {/* Feature Preview */}
// // //           <div className="mt-16 p-8 rounded-xl bg-background/50 border border-border/50 terminal-box space-y-4">
// // //             <h3 className="font-mono font-semibold text-accent glow-text mb-4">Upcoming Features</h3>
// // //             <ul className="space-y-2 font-mono text-sm">
// // //               <li className="text-muted-foreground">
// // //                 {"> "}
// // //                 <span className="text-accent">Live threat feeds</span>
// // //               </li>
// // //               <li className="text-muted-foreground">
// // //                 {"> "}
// // //                 <span className="text-accent">Behavioral analysis</span>
// // //               </li>
// // //               <li className="text-muted-foreground">
// // //                 {"> "}
// // //                 <span className="text-accent">Anomaly detection</span>
// // //               </li>
// // //               <li className="text-muted-foreground">
// // //                 {"> "}
// // //                 <span className="text-accent">Alert correlations</span>
// // //               </li>
// // //               <li className="text-muted-foreground">
// // //                 {"> "}
// // //                 <span className="text-accent">Automated response</span>
// // //               </li>
// // //             </ul>
// // //           </div>
// // //         </section>
// // //       </main>
// // //     </>
// // //   )
// // // }

// // // function PlaceholderCard({ title, description, icon }: { title: string; description: string; icon: React.ReactNode }) {
// // //   return (
// // //     <Card className="bg-card/50 border-accent/20 hover:border-accent/50 transition-all duration-300 glow-border">
// // //       <CardHeader>
// // //         <div className="text-accent mb-3">{icon}</div>
// // //         <CardTitle className="font-mono text-lg">{title}</CardTitle>
// // //       </CardHeader>
// // //       <CardContent>
// // //         <CardDescription className="text-muted-foreground">{description}</CardDescription>
// // //       </CardContent>
// // //     </Card>
// // //   )
// // // }
// // // // "use client"

// // // // import { useState, ReactNode } from "react"

// // // // import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
// // // // import { Button } from "@/components/ui/button"
// // // // import { Input } from "@/components/ui/input"

// // // // import { Activity, Brain } from "lucide-react"

// // // // /* ---------- Types ---------- */
// // // // type XAIItem = {
// // // //   feature: string
// // // //   impact: number
// // // // }

// // // // type PredictionResult = {
// // // //   prediction: string
// // // //   confidence: number
// // // //   explanation: XAIItem[]
// // // // }

// // // // export default function IDSPage() {
// // // //   const [features, setFeatures] = useState<number[]>(Array(7).fill(0))
// // // //   const [loading, setLoading] = useState(false)
// // // //   const [result, setResult] = useState<PredictionResult | null>(null)

// // // //   const handleChange = (index: number, value: string) => {
// // // //     const updated = [...features]
// // // //     updated[index] = Number(value)
// // // //     setFeatures(updated)
// // // //   }

// // // //   const analyzeTraffic = async () => {
// // // //     setLoading(true)
// // // //     setResult(null)

// // // //     try {
// // // //       const res = await fetch("http://localhost:9000/predict", {
// // // //         method: "POST",
// // // //         headers: {
// // // //           "Content-Type": "application/json",
// // // //         },
// // // //         body: JSON.stringify({
// // // //           features: features, // ✅ FIXED
// // // //         }),
// // // //       })

// // // //       if (!res.ok) {
// // // //         throw new Error("Backend error")
// // // //       }

// // // //       const data: PredictionResult = await res.json()
// // // //       setResult(data)
// // // //     } catch (err) {
// // // //       console.error(err)
// // // //       setResult(null)
// // // //     } finally {
// // // //       setLoading(false)
// // // //     }
// // // //   }

// // // //   return (
// // // //     <main className="min-h-screen bg-background">
// // // //       <section className="relative max-w-7xl mx-auto px-6 py-24 space-y-16">

// // // //         {/* Header */}
// // // //         <div>
// // // //           <h1 className="text-4xl font-bold font-mono mb-4">
// // // //             Intrusion Detection System
// // // //           </h1>
// // // //           <p className="text-lg text-muted-foreground">
// // // //             Real-time threat detection with Explainable AI
// // // //           </p>
// // // //         </div>

// // // //         <div className="grid md:grid-cols-2 gap-8">

// // // //           {/* INPUT */}
// // // //           <Card className="bg-card/50">
// // // //             <CardHeader>
// // // //               <CardTitle className="font-mono flex items-center gap-2">
// // // //                 <Activity className="text-accent" />
// // // //                 Traffic Input
// // // //               </CardTitle>
// // // //               <CardDescription>
// // // //                 Enter PCA-transformed network features
// // // //               </CardDescription>
// // // //             </CardHeader>

// // // //             <CardContent className="space-y-4">
// // // //               {features.map((_, i) => (
// // // //                 <Input
// // // //                   key={i}
// // // //                   type="number"
// // // //                   placeholder={`Principal Component ${i + 1}`}
// // // //                   onChange={(e) => handleChange(i, e.target.value)}
// // // //                 />
// // // //               ))}

// // // //               <Button
// // // //                 className="w-full mt-4"
// // // //                 onClick={analyzeTraffic}
// // // //                 disabled={loading}
// // // //               >
// // // //                 {loading ? "Analyzing..." : "Analyze Traffic"}
// // // //               </Button>
// // // //             </CardContent>
// // // //           </Card>

// // // //           {/* OUTPUT */}
// // // //           <Card className="bg-card/50">
// // // //             <CardHeader>
// // // //               <CardTitle className="font-mono flex items-center gap-2">
// // // //                 <Brain className="text-accent" />
// // // //                 Model Output & XAI
// // // //               </CardTitle>
// // // //               <CardDescription>
// // // //                 Prediction, confidence, and explanation
// // // //               </CardDescription>
// // // //             </CardHeader>

// // // //             <CardContent>
// // // //               {!result ? (
// // // //                 <p className="text-muted-foreground text-sm">
// // // //                   Awaiting analysis input...
// // // //                 </p>
// // // //               ) : (
// // // //                 <div className="space-y-6">

// // // //                   {/* Prediction */}
// // // //                   <div>
// // // //                     <p className="font-mono text-accent">{"> Prediction"}</p>
// // // //                     <p className="text-lg font-semibold">
// // // //                       {result.prediction}
// // // //                     </p>
// // // //                     <p className="text-sm text-muted-foreground">
// // // //                       Confidence: {(result.confidence * 100).toFixed(2)}%
// // // //                     </p>
// // // //                   </div>

// // // //                   {/* XAI */}
// // // //                   <div>
// // // //                     <p className="font-mono text-accent mb-2">
// // // //                       {"> XAI Feature Importance"}
// // // //                     </p>

// // // //                     <div className="space-y-2">
// // // //                       {result.explanation.map((f, idx) => (
// // // //                         <div key={idx}>
// // // //                           <div className="flex justify-between text-sm">
// // // //                             <span>{f.feature}</span>
// // // //                             <span>{(Math.abs(f.impact) * 100).toFixed(1)}%</span>
// // // //                           </div>
// // // //                           <div className="h-2 bg-muted rounded">
// // // //                             <div
// // // //                               className="h-2 bg-accent rounded"
// // // //                               style={{ width: `${Math.abs(f.impact) * 100}%` }}
// // // //                             />
// // // //                           </div>
// // // //                         </div>
// // // //                       ))}
// // // //                     </div>
// // // //                   </div>

// // // //                 </div>
// // // //               )}
// // // //             </CardContent>
// // // //           </Card>

// // // //         </div>
// // // //       </section>
// // // //     </main>
// // // //   )
// // // // }
