"use client"

import { useState } from "react"
import { Loader } from "@/components/loader"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card"
import { Play, Brain, ShieldAlert, Sparkles, FileDown } from "lucide-react"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts"
import jsPDF from "jspdf"

type FlowPrediction = {
  prediction?: any
  label?: string
  confidence?: number
  error?: string
}

export default function IDSPage() {
  const [pcapFile, setPcapFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<FlowPrediction[]>([])
  const [error, setError] = useState<string | null>(null)
  const [flowsCount, setFlowsCount] = useState<number>(0)
  const [explainChart, setExplainChart] = useState<any[]>([])


  const [xai, setXai] = useState<any>(null)
  const [geminiAnalysis, setGeminiAnalysis] = useState<any>(null)
  const [severity, setSeverity] = useState<number>(0)

  const CONFIDENCE_THRESHOLD = 0.0

  /* ---------------- FILE UPLOAD ---------------- */
  const handlePCAPUpload = (e: any) => {
    const file = e.target.files[0]
    if (!file) return

    if (!file.name.endsWith(".pcap")) {
      setError("Upload valid .pcap")
      return
    }

    setPcapFile(file)
    setError(null)
    setResults([])
    setGeminiAnalysis("")
    setXai(null)
  }
  /* ---------------- GEMINI ---------------- */
  /* ---------------- GEMINI SOC (FASTAPI BACKEND) ---------------- */
const runGeminiAnalysis = async (xaiData: any, predictions: any[]) => {
  try {
    const res = await fetch("http://localhost:9000/ids/gemini-soc", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        xai: xaiData,
        predictions: predictions,
      }),
    })

    if (!res.ok) throw new Error("Gemini SOC failed")

    const data = await res.json()

    /*
      Expected backend response:
      {
        soc_analysis: {...},
        threat_score: 87,
        severity: "Critical"
      }
    */

    // pretty formatted SOC analysis
    setGeminiAnalysis(data.soc_analysis)

    // 🔥 REAL threat score from LLM (not fake 25/50/75)
    setSeverity(data.threat_score || 0)

  } catch (err) {
    console.error(err)
    setGeminiAnalysis("Gemini SOC analysis failed")
    setSeverity(0)
  }
}


  /* ---------------- IDS RUN ---------------- */
  const runIDS = async () => {
    if (!pcapFile) {
      setError("Upload PCAP first")
      return
    }

    setLoading(true)
    setError(null)
    setResults([])
    setGeminiAnalysis("")
    setXai(null)

    try {
      const formData = new FormData()
      formData.append("file", pcapFile)

      const res = await fetch("http://localhost:9000/ids/pcap", {
        method: "POST",
        body: formData,
      })

      const data = await res.json()
      console.log("FULL API RESPONSE:", data)
      if (!res.ok) throw new Error(data?.detail || "IDS failed")

      setFlowsCount(data.flows_processed || 0)
      setResults(data.predictions || [])

      // generic XAI
      if (data.xai) {
        setXai(data.xai)
        await runGeminiAnalysis(data.xai, data.predictions || [])
      }
      // 🔥 find first prediction that has XAI
      let explainData = null

      for (const p of data.predictions || []) {
        if (p?.xai?.data && Array.isArray(p.xai.data)) {
          explainData = p.xai.data
          break
        }
      }

      console.log("Explain raw:", explainData)

      if (explainData) {
        setExplainChart(explainData)
        console.log("✅ SHAP graph loaded:", explainData.length)
      } else {
        console.log("❌ No SHAP data found in any flow")
      }


    } catch (err: any) {
      setError(err.message || "Server error")
    } finally {
      setLoading(false)
    }
  }

  /* ---------------- PDF REPORT ---------------- */
  const downloadPDF = () => {
    const doc = new jsPDF()
    doc.setFontSize(18)
    doc.text("Network Intrusion Detection Report", 20, 20)

    doc.setFontSize(12)
    doc.text(`Flows analyzed: ${flowsCount}`, 20, 40)
    doc.text(`High risk flows: ${results.length}`, 20, 50)

    if (geminiAnalysis) {
      doc.text("AI SOC Analysis:", 20, 70)
      doc.setFontSize(10)
      doc.text(doc.splitTextToSize(geminiAnalysis, 170), 20, 80)
    }

    doc.save("IDS_Report.pdf")
  }

  /* ---------------- SHAP GRAPH DATA ---------------- */
  let shapData: any[] = []
  if (xai?.feature_importance) {
    shapData = Object.entries(xai.feature_importance).map(([k, v]: any) => ({
      name: k,
      value: Number(v),
    }))
  }

  return (
    <main className="min-h-screen bg-background">
      <section className="max-w-7xl mx-auto px-6 py-12">

        {/* HEADER */}
        <div className="mb-10">
          <h1 className="text-4xl font-bold font-mono">
            AI Intrusion Detection Dashboard
          </h1>
        </div>

        {/* UPLOAD */}
        <Card className="mb-10">
          <CardHeader>
            <CardTitle>Upload PCAP</CardTitle>
            <CardDescription>Run full IDS pipeline</CardDescription>
          </CardHeader>

          <CardContent className="space-y-4">
            <input type="file" accept=".pcap" onChange={handlePCAPUpload} />

            {error && <p className="text-red-400">{error}</p>}

            <button
              onClick={runIDS}
              disabled={loading || !pcapFile}
              className="w-full bg-accent/20 p-3 rounded-lg font-mono"
            >
              <Play className="inline mr-2" />
              {loading ? "Analyzing..." : "Run IDS"}
            </button>
          </CardContent>
        </Card>

        {/* LOADER */}
        {loading && (
          <Card className="mb-10">
            <CardContent className="py-12">
              <Loader />
              <p className="text-center mt-4">Running full pipeline...</p>
            </CardContent>
          </Card>
        )}

        {/* 🔥 SEVERITY METER */}
        {(severity > 0 || results.length > 0) && (
          <Card className="mb-10 border-red-500/30 bg-gradient-to-br from-black to-red-950/40">
            <CardHeader>
              <CardTitle className="flex items-center gap-3 text-red-400 text-2xl font-mono">
                <ShieldAlert size={28} />
                LIVE THREAT LEVEL
              </CardTitle>
              <CardDescription>
                Real-time AI intrusion risk analysis
              </CardDescription>
            </CardHeader>

            <CardContent>
              {/* meter */}
              <div className="w-full bg-black/40 rounded-full h-10 overflow-hidden border border-red-500/20">
                <div
                  className="h-10 bg-gradient-to-r from-green-400 via-yellow-400 to-red-600 transition-all duration-[2000ms] ease-out"
                  style={{ width: `${severity}%` }}
                />
              </div>

              <div className="flex justify-between mt-3 font-mono text-sm">
                <span className="text-green-400">LOW</span>
                <span className="text-yellow-400">MEDIUM</span>
                <span className="text-red-400">CRITICAL</span>
              </div>

              <p className="mt-4 text-3xl font-bold font-mono text-red-400">
                {severity}% Threat Score
              </p>
            </CardContent>
          </Card>
        )}


        {/* 🧠 XAI */}
        {/* ================= XAI BLOCK ================= */}
        {xai && (
          <Card className="mb-10 border-purple-500/30 bg-gradient-to-br from-black to-purple-950/40">
            <CardHeader>
              <CardTitle className="text-xl font-mono flex gap-2">
                <Brain className="text-purple-400" />
                Explainable AI Analysis
              </CardTitle>
              <CardDescription>
                Why the model flagged this traffic
              </CardDescription>
            </CardHeader>

            <CardContent className="grid md:grid-cols-2 gap-6">
              
              {/* left */}
              <div className="bg-black/40 p-4 rounded-xl border border-purple-500/20">
                <p className="text-purple-300 font-mono mb-2">Raw XAI Output</p>
                <pre className="text-xs whitespace-pre-wrap text-muted-foreground">
                  {JSON.stringify(xai, null, 2)}
                </pre>
              </div>

              {/* right */}
              <div className="bg-black/40 p-4 rounded-xl border border-purple-500/20">
                <p className="text-purple-300 font-mono mb-2">
                  AI Explanation Summary
                </p>
                <p className="text-sm text-muted-foreground font-mono">
                  This section highlights the most influential network flow
                  features responsible for triggering intrusion detection.
                  High packet rate, abnormal flow duration, or suspicious
                  port usage typically indicates attack behavior.
                </p>
              </div>
            </CardContent>
          </Card>
        )}


        {/* 🧠 SHAP GRAPH */}
        {/* ================= ATTACK GRAPH ================= */}
        {/* {results.length > 0 && (
          <Card className="mb-10 border-cyan-500/30 bg-gradient-to-br from-black to-cyan-950/30">
            <CardHeader>
              <CardTitle className="text-xl font-mono flex gap-2">
                📊 Traffic Classification Distribution
              </CardTitle>
              <CardDescription>
                Normal vs Suspicious traffic breakdown
              </CardDescription>
            </CardHeader>

            <CardContent style={{ height: 320 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={[
                    {
                      name: "Normal",
                      value: results.filter(r => r.label === "Normal").length,
                    },
                    {
                      name: "Attack",
                      value: results.filter(r => r.label !== "Normal").length,
                    },
                  ]}
                >
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="value" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        )} */}
        {/* ================= SHAP FEATURE IMPACT ================= */}
        {explainChart.length > 0 && (
          <Card className="mb-10 border-cyan-500/30 bg-gradient-to-br from-black to-cyan-950/30">
            <CardHeader>
              <CardTitle className="text-xl font-mono text-cyan-400">
                🔬 Feature Impact Analysis (SHAP)
              </CardTitle>
              <CardDescription>
                Features influencing intrusion detection decision
              </CardDescription>
            </CardHeader>

            <CardContent style={{ height: 420 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={[...explainChart].sort((a,b)=>Math.abs(b.impact)-Math.abs(a.impact))}
                  layout="vertical"
                >
                  <XAxis
                    type="number"
                    tick={{ fill: "#00ffe1" }}
                    axisLine={{ stroke: "#00ffe1" }}
                  />
                  <YAxis
                    dataKey="feature"
                    type="category"
                    width={220}
                    tick={{ fill: "#9be7ff", fontSize: 12 }}
                  />
                  <Tooltip />

                  <Bar dataKey="impact">
                    {explainChart.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={entry.impact > 0 ? "#00ff9c" : "#ff4d6d"}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        )}



        {/* ================= LLM SOC ANALYSIS ================= */}
        {/* {geminiAnalysis && (
          <Card className="mb-10 border-emerald-500/30 bg-gradient-to-br from-black to-emerald-950/30">
            <CardHeader>
              <CardTitle className="flex gap-2 text-emerald-400 text-xl font-mono">
                <Sparkles />
                AI Security Operations Report
              </CardTitle>
              <CardDescription>
                Generated by Gemini SOC Analyst
              </CardDescription>
            </CardHeader>

            <CardContent className="space-y-6">

              <div className="bg-black/40 border border-emerald-500/20 rounded-xl p-5">
                <pre className="whitespace-pre-wrap text-sm font-mono text-muted-foreground">
                  {geminiAnalysis}
                </pre>
              </div>

              <button
                onClick={downloadPDF}
                className="flex items-center gap-2 bg-emerald-500/20 hover:bg-emerald-500/40 px-6 py-3 rounded-lg font-mono"
              >
                <FileDown size={16} />
                Download Full Incident Report
              </button>
            </CardContent>
          </Card>
        )} */}
        {/* ================= AI SOC REPORT ================= */}
        {geminiAnalysis && (
          <Card className="mb-10 border-emerald-500/30 bg-gradient-to-br from-black to-emerald-950/30 shadow-xl">
            <CardHeader>
              <CardTitle className="flex gap-2 text-emerald-400 text-2xl font-mono">
                <Sparkles />
                AI Security Operations Report
              </CardTitle>
              <CardDescription>
                Real-time AI SOC threat intelligence
              </CardDescription>
            </CardHeader>

            <CardContent className="space-y-6 font-mono">

              {/* ATTACK TYPE */}
              <div className="grid md:grid-cols-3 gap-4">
                <div className="bg-black/40 p-4 rounded-xl border border-emerald-500/20">
                  <p className="text-emerald-300 text-sm">Attack Type</p>
                  <p className="text-lg font-bold text-emerald-400">
                    {geminiAnalysis.attack_type}
                  </p>
                </div>

                <div className="bg-black/40 p-4 rounded-xl border border-emerald-500/20">
                  <p className="text-emerald-300 text-sm">Severity</p>
                  <p className="text-lg font-bold text-red-400">
                    {geminiAnalysis.severity}
                  </p>
                </div>

                <div className="bg-black/40 p-4 rounded-xl border border-emerald-500/20">
                  <p className="text-emerald-300 text-sm">Confidence</p>
                  <p className="text-lg font-bold text-cyan-400">
                    {geminiAnalysis.confidence}%
                  </p>
                </div>
              </div>

              {/* WHY FLAGGED */}
              <div className="bg-black/40 border border-emerald-500/20 rounded-xl p-5">
                <p className="text-emerald-300 mb-2">Why IDS flagged this</p>
                <p className="text-sm text-muted-foreground">
                  {geminiAnalysis.why_flagged}
                </p>
              </div>

              {/* IMPACT */}
              <div className="bg-black/40 border border-emerald-500/20 rounded-xl p-5">
                <p className="text-emerald-300 mb-2">Real World Impact</p>
                <p className="text-sm text-muted-foreground">
                  {geminiAnalysis.real_world_impact}
                </p>
              </div>

              {/* MITIGATION */}
              <div className="bg-black/40 border border-emerald-500/20 rounded-xl p-5">
                <p className="text-emerald-300 mb-3">Recommended Mitigation</p>

                <ul className="space-y-2 text-sm">
                  {geminiAnalysis.mitigation_steps?.map((m: string, i: number) => (
                    <li key={i} className="bg-black/30 p-3 rounded border border-emerald-500/10">
                      {m}
                    </li>
                  ))}
                </ul>
              </div>

              {/* DOWNLOAD */}
              <button
                onClick={downloadPDF}
                className="flex items-center gap-2 bg-emerald-500/20 hover:bg-emerald-500/40 px-6 py-3 rounded-lg font-mono"
              >
                <FileDown size={16} />
                Download Full Incident Report
              </button>

            </CardContent>
          </Card>
        )}



        {/* FLOWS */}
        {!loading && results.length > 0 && (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold font-mono">
              High Confidence Flows
            </h2>

            {results
              .filter((r) => (r.confidence || 0) >= CONFIDENCE_THRESHOLD)
              .slice(0, 25)
              .map((r, i) => (
                <Card key={i}>
                  <CardContent className="font-mono text-sm py-4">
                    <p>
                      Prediction:
                      <span
                        className={
                          r.label === "Attack"
                            ? "text-red-400 ml-2"
                            : "text-green-400 ml-2"
                        }
                      >
                        {r.label}
                      </span>
                    </p>
                    <p>Confidence: {(r.confidence! * 100).toFixed(2)}%</p>
                  </CardContent>
                </Card>
              ))}
          </div>
        )}
      </section>
    </main>
  )
}


// "use client"

// import { useState } from "react"
// import { Loader } from "@/components/loader"
// import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
// import { Upload, Brain, Play } from "lucide-react"

// type FlowPrediction = {
// prediction?: any
// label?: string
// confidence?: number
// error?: string
// }

// export default function IDSPage() {
// const [pcapFile, setPcapFile] = useState<File | null>(null)
// const [loading, setLoading] = useState(false)
// const [results, setResults] = useState<FlowPrediction[]>([])
// const [error, setError] = useState<string | null>(null)
// const [flowsCount, setFlowsCount] = useState<number>(0)

// /* ---------------- PCAP UPLOAD ---------------- */
// const handlePCAPUpload = (e: any) => {
// const file = e.target.files[0]
// if (!file) return


// if (!file.name.endsWith(".pcap")) {
//   setError("Please upload a valid .pcap file")
//   return
// }

// setPcapFile(file)
// setError(null)
// setResults([])


// }

// /* ---------------- RUN IDS PIPELINE ---------------- */
// const runIDS = async () => {
// if (!pcapFile) {
// setError("Upload a PCAP file first")
// return
// }


// setLoading(true)
// setError(null)
// setResults([])

// try {
//   const formData = new FormData()
//   formData.append("file", pcapFile)

//   // 🔥 change to your backend URL
//   const res = await fetch("http://localhost:9000/ids/pcap", {
//     method: "POST",
//     body: formData,
//   })

//   const data = await res.json()

//   if (!res.ok) throw new Error(data?.detail || "IDS pipeline failed")

//   setFlowsCount(data.flows_processed || 0)
//   setResults(data.predictions || [])

// } catch (err: any) {
//   setError(err.message || "Server error")
// } finally {
//   setLoading(false)
// }


// }

// return ( <main className="min-h-screen bg-background">


//   {/* GRID BACKGROUND */}
//   <div className="fixed inset-0 opacity-5 pointer-events-none">
//     <div
//       className="absolute inset-0"
//       style={{
//         backgroundImage:
//           "linear-gradient(0deg, rgba(0,255,150,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(0,255,150,0.1) 1px, transparent 1px)",
//         backgroundSize: "50px 50px",
//       }}
//     ></div>
//   </div>

//   <section className="relative max-w-7xl mx-auto px-6 py-12">

//     {/* HEADER */}
//     <div className="mb-12">
//       <h1 className="text-4xl md:text-5xl font-bold font-mono mb-4">
//         <span className="cyber-gradient-text">PCAP</span>
//         <br />
//         Intrusion Detection
//       </h1>
//       <p className="text-muted-foreground">
//         Upload PCAP file → CICFlowMeter → AI model → detect network attacks
//       </p>
//     </div>

//     {/* MAIN CARD */}
//     <Card className="mb-12 bg-card/50 border-accent/20 glow-border">
//       <CardHeader>
//         <CardTitle className="font-mono">IDS Pipeline</CardTitle>
//         <CardDescription>Upload PCAP network capture file</CardDescription>
//       </CardHeader>

//       <CardContent className="space-y-6">

//         {/* PCAP UPLOAD */}
//         <div className="space-y-2">
//           <label className="block text-sm font-mono text-foreground">
//             Upload PCAP File
//           </label>

//           <input
//             type="file"
//             accept=".pcap"
//             onChange={handlePCAPUpload}
//             disabled={loading}
//             className="w-full px-4 py-3 rounded-lg bg-background/50 border border-border/50 focus:border-accent/50 text-foreground focus:outline-none transition-colors font-mono text-sm"
//           />
//         </div>

//         {/* ERROR */}
//         {error && (
//           <div className="p-4 rounded-lg bg-red-400/10 border border-red-400/30">
//             <p className="text-sm text-red-400 font-mono">{error}</p>
//           </div>
//         )}

//         {/* RUN BUTTON */}
//         <button
//           onClick={runIDS}
//           disabled={loading || !pcapFile}
//           className="w-full cyber-button flex items-center justify-center gap-2 px-6 py-3 bg-accent/20 hover:bg-accent/40 text-accent border border-accent/50 rounded-lg font-mono font-semibold transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
//         >
//           <Play className="w-4 h-4" />
//           {loading ? "Analyzing Network Traffic..." : "Run IDS Pipeline"}
//         </button>
//       </CardContent>
//     </Card>

//     {/* LOADER */}
//     {loading && (
//       <div className="mb-12">
//         <Card className="bg-card/50 border-accent/20">
//           <CardContent className="py-12">
//             <Loader />
//             <p className="text-center font-mono text-sm mt-4 text-muted-foreground">
//               Running CICFlowMeter + AI model... this may take 30–90 sec
//             </p>
//           </CardContent>
//         </Card>
//       </div>
//     )}

//     {/* RESULTS */}
//     {!loading && results.length > 0 && (
//       <div className="space-y-10 mt-10">
//         <h2 className="text-3xl font-bold font-mono">
//           IDS Results ({flowsCount} flows analyzed)
//         </h2>

//         {results.slice(0, 20).map((r, i) => (
//           <Card key={i} className="border-accent/40 bg-card/50">
//             <CardHeader>
//               <CardTitle className="font-mono flex items-center gap-2">
//                 <Brain className="text-accent" />
//                 Flow #{i + 1}
//               </CardTitle>
//             </CardHeader>

//             <CardContent className="space-y-2 font-mono text-sm">
//               {r.error ? (
//                 <p className="text-red-400">{r.error}</p>
//               ) : (
//                 <>
//                   <p>
//                     Prediction:{" "}
//                     <span
//                       className={
//                         r.label === "Attack"
//                           ? "text-red-400 font-bold"
//                           : "text-green-400 font-bold"
//                       }
//                     >
//                       {r.label || r.prediction}
//                     </span>
//                   </p>

//                   {r.confidence !== undefined && (
//                     <p className="text-muted-foreground">
//                       Confidence: {(r.confidence * 100).toFixed(3)}%
//                     </p>
//                   )}
//                 </>
//               )}
//             </CardContent>
//           </Card>
//         ))}
//       </div>
//     )}

//     {/* PLACEHOLDER */}
//     {!loading && results.length === 0 && !error && (
//       <Card className="bg-card/50 border-border/50">
//         <CardContent className="py-12 text-center">
//           <p className="text-muted-foreground font-mono">
//             Upload a PCAP file and click "Run IDS Pipeline" to detect attacks
//           </p>
//         </CardContent>
//       </Card>
//     )}

//   </section>
// </main>


// )
// }
// -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

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
