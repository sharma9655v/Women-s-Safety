"use client";
import { useState } from "react";
import { useQuery } from "@/lib/query";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { formatDistance, timeAgo } from "@/lib/format";
import { Loader2, Send, MapPin, Shield, AlertTriangle, Camera, Image, X, Check, Map, FileText, XCircle } from "lucide-react";

export default function ReportPage() {
  const [step, setStep] = useState<"location" | "details" | "confirm">("location");
  const [location, setLocation] = useState({ lat: 28.6139, lon: 77.209, name: "Current location" });
  const [category, setCategory] = useState("");
  const [description, setDescription] = useState("");
  const [image, setImage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [segments, setSegments] = useState<{ segment_id: number; risk: number; name: string }[]>([]);

  const categories = [
    { id: "harassment", label: "Harassment", icon: AlertTriangle },
    { id: "poor_lighting", label: "Poor Lighting", icon: Shield },
    { id: "road_hazard", label: "Road Hazard", icon: AlertTriangle },
    { id: "suspicious_activity", label: "Suspicious Activity", icon: AlertTriangle },
    { id: "streetlight_not_working", label: "Streetlight Not Working", icon: Shield },
    { id: "other", label: "Other", icon: AlertTriangle },
  ];

  const detectLocation = async () => {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(p => {
      setLocation({ lat: p.coords.latitude, lon: p.coords.longitude, name: "Current location" });
      // In real app, reverse geocode here
    });
  };

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) {
      const reader = new FileReader();
      reader.onload = () => setImage(reader.result as string);
      reader.readAsDataURL(f);
    }
  };

  const next = () => {
    if (step === "location" && category) setStep("details");
    else if (step === "details") setStep("confirm");
  };
  const back = () => setStep(step === "details" ? "location" : step === "confirm" ? "details" : "location");

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      // Find nearest segment - simplified
      const segmentId = segments[0]?.segment_id ?? 1;
      await api.reports.submit({ segment_id: segmentId, category, description, evidence_image: image });
      setSuccess(true);
      setStep("location");
      setCategory("");
      setDescription("");
      setImage(null);
    } catch { alert("Failed to submit report"); }
    finally { setLoading(false); }
  };

  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col">
      <div className="p-4 sm:p-6 border-b border-line">
        <div className="mx-auto max-w-xl">
          <h1 className="font-display text-2xl font-bold">Submit Safety Report</h1>
          <p className="text-sm text-text-mid">Anonymous, evidence-based reports help improve routing for everyone.</p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        <div className="mx-auto max-w-xl space-y-4">
          {/* Progress */}
          <div className="flex items-center gap-2">
            {["Location", "Details", "Confirm"].map((s, i) => (
              <div key={s} className="flex-1 flex items-center">
                <div className={`flex-1 h-1 rounded ${i < (step === "location" ? 0 : step === "details" ? 1 : 2) ? "bg-primary" : "bg-line"}`} />
                {i < 2 && <span className="mx-2 text-text-low">→</span>}
              </div>
            ))}
          </div>

          {success && (
            <Card variant="glass" className="text-center py-8 animate-in">
              <Check size={48} className="mx-auto text-safe mb-4" />
              <h3 className="font-display text-xl font-semibold">Report Submitted</h3>
              <p className="text-text-mid mt-2">Thank you. Your report helps keep the community safer.</p>
              <Button className="mt-6" onClick={() => setSuccess(false)}>Submit Another</Button>
            </Card>
          )}

          {!success && (
            <>
              {step === "location" && (
                <Card variant="glass" className="space-y-4">
                  <h3 className="font-medium flex items-center gap-2"><MapPin size={20} className="text-accent" /> Where did this happen?</h3>
                  <div className="flex gap-2">
                    <Button variant="outline" className="flex-1" onClick={detectLocation}><Loader2 size={16} className="animate-spin" /> Use Current Location</Button>
                    <Button variant="ghost" onClick={() => { /* open map picker */}}><Map size={16} /></Button>
                  </div>
                  <p className="text-sm text-text-mid">Location: {location.name} ({location.lat.toFixed(4)}, {location.lon.toFixed(4)})</p>
                  <div className="grid gap-2 sm:grid-cols-3">
                    {categories.map(c => (
                      <label key={c.id} className={`relative cursor-pointer ${category === c.id ? "ring-2 ring-primary" : ""}`}>
                        <input type="radio" name="category" value={c.id} checked={category === c.id} onChange={() => setCategory(c.id)} className="sr-only" />
                        <div className="glass p-4 rounded-xl text-center transition-colors hover:border-primary/30">
                          <c.icon size={24} className="mx-auto mb-2 text-accent" />
                          <span className="text-sm font-medium">{c.label}</span>
                        </div>
                      </label>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <Button variant="ghost" onClick={back} disabled={step === "location"}><X size={16} /> Back</Button>
                    <Button className="flex-1" disabled={!category} onClick={next}>Next <FileText size={16} /></Button>
                  </div>
                </Card>
              )}

              {step === "details" && (
                <Card variant="glass" className="space-y-4">
                  <h3 className="font-medium flex items-center gap-2"><FileText size={20} className="text-accent" /> Details</h3>
                  <Input label="Description" placeholder="What happened? (optional)" value={description} onChange={e => setDescription(e.target.value)} />
                  <div className="space-y-3">
                    <label className="flex items-center gap-3 cursor-pointer">
                      <input type="checkbox" className="accent-primary" /> Include photo evidence
                    </label>
                    {image ? (
                      <div className="relative glass p-2 rounded-xl">
                        <img src={image} alt="Evidence" className="max-h-64 rounded-lg" />
                        <button onClick={() => setImage(null)} className="absolute top-2 right-2 p-1 rounded-lg bg-black/50 text-white"><X size={16} /></button>
                      </div>
                    ) : (
                      <label className="flex items-center justify-center gap-2 p-6 border-2 border-dashed border-line rounded-xl cursor-pointer hover:border-primary/30">
                        <Camera size={24} className="text-text-low" />
                        <span className="text-text-mid">Tap to add photo</span>
                        <input type="file" accept="image/*" className="sr-only" onChange={handleImageChange} />
                      </label>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <Button variant="ghost" onClick={back}><X size={16} /> Back</Button>
                    <Button className="flex-1" onClick={next}>Next <Shield size={16} /></Button>
                  </div>
                </Card>
              )}

              {step === "confirm" && (
                <Card variant="glass" className="space-y-4">
                  <h3 className="font-medium flex items-center gap-2"><Shield size={20} className="text-primary" /> Confirm & Submit</h3>
                  <div className="glass p-3 rounded-xl space-y-2 text-sm">
                    <div className="flex justify-between"><span className="text-text-mid">Category</span><span className="font-medium">{categories.find(c => c.id === category)?.label}</span></div>
                    <div className="flex justify-between"><span className="text-text-mid">Location</span><span className="font-medium">{location.name}</span></div>
                    {description && <div className="flex justify-between"><span className="text-text-mid">Description</span><span className="font-medium">{description.slice(0, 50)}…</span></div>}
                    {image && <div className="flex justify-between"><span className="text-text-mid">Photo</span><span className="font-medium text-safe">Attached</span></div>}
                  </div>
                  <p className="text-xs text-text-low text-center">This report is anonymous. No personal identifiers are stored.</p>
                  <div className="flex gap-2">
                    <Button variant="ghost" onClick={back}><X size={16} /> Back</Button>
                    <Button className="flex-1" onClick={submit} disabled={loading}><Send size={16} /> {loading ? "Submitting…" : "Submit Report"}</Button>
                  </div>
                </Card>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}