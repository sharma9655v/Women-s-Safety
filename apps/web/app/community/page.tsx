"use client";

import { MessageSquarePlus, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { CommunityFeed } from "@/app/components/insights/CommunityFeed";
import { Button } from "@/app/components/ui/Button";
import { Card, CardHeader } from "@/app/components/ui/Card";
import { Input, Select } from "@/app/components/ui/Input";
import { SkeletonCard } from "@/app/components/ui/Skeleton";
import { fetchCommunity, submitCommunityPost } from "@/lib/api";
import type { CommunityPost } from "@/lib/types";

const KINDS = [
  { id: "route_update", label: "Route update" },
  { id: "photo", label: "Photo / visual evidence" },
  { id: "alert", label: "Alert" },
];

export default function CommunityPage() {
  const [posts, setPosts] = useState<CommunityPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [kind, setKind] = useState("route_update");
  const [location, setLocation] = useState("");
  const [text, setText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [published, setPublished] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetchCommunity()
      .then((p) => {
        if (!cancelled) setPosts(p);
      })
      .catch(() => {
        if (!cancelled) setPosts([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const canPost = text.trim().length >= 10 && location.trim().length >= 2;

  const publish = async () => {
    if (!canPost || submitting) return;
    setSubmitting(true);
    setError(null);
    setPublished(false);
    try {
      await submitCommunityPost({
        kind: kind as "route_update" | "photo" | "alert",
        location: location.trim(),
        text: text.trim(),
      });
      setPublished(true);
      setText("");
      setLocation("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not publish the update. Try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-3xl space-y-4 p-4 lg:p-6">
        <header>
          <h1 className="flex items-center gap-2 text-xl font-bold text-foreground">
            <span className="text-primary">Community</span>
            <ShieldCheck className="size-5 text-info" aria-label="Anonymous community" />
          </h1>
          <p className="text-sm text-text-muted">
            Anonymous route updates from women in your city. Authorship is never shown — verified
            posts carry a Verified badge only after review.
          </p>
        </header>

        <Card>
          <CardHeader
            title="Share an update"
            subtitle="Help others — never share anyone's identity or private details."
          />
          <div className="space-y-3">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <Select
                id="post-kind"
                label="Type"
                value={kind}
                onChange={(e) => setKind(e.target.value)}
              >
                {KINDS.map((k) => (
                  <option key={k.id} value={k.id}>
                    {k.label}
                  </option>
                ))}
              </Select>
              <Input
                label="Location"
                placeholder="e.g. Tilak Marg"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                maxLength={60}
              />
            </div>
            <Input
              label="What should others know?"
              placeholder="Describe what you saw — facts only, e.g. 'footpath reopened', 'new streetlight installed'."
              value={text}
              onChange={(e) => setText(e.target.value)}
              maxLength={280}
              hint={`${text.length}/280`}
            />
            <div className="flex items-center justify-between gap-3">
              <p className="text-[11px] text-text-muted">
                Published anonymously — your identity is never shown. Posts appear in the feed after
                a moderator verifies them.
              </p>
              <Button
                size="sm"
                loading={submitting}
                disabled={!canPost}
                onClick={() => void publish()}
              >
                <MessageSquarePlus className="size-3.5" aria-hidden /> Post update
              </Button>
            </div>
            {error ? (
              <p
                role="alert"
                className="rounded-xl border border-danger/25 bg-danger/8 px-3 py-2 text-xs text-danger"
              >
                {error}
              </p>
            ) : null}
            {published ? (
              <p
                role="status"
                className="rounded-xl border border-success/25 bg-success/8 px-3 py-2 text-xs text-success"
              >
                Update submitted for review. Thank you for helping your community.
              </p>
            ) : null}
          </div>
        </Card>

        {loading ? (
          <div className="space-y-3">
            <SkeletonCard rows={2} />
            <SkeletonCard rows={2} />
          </div>
        ) : (
          <div className="h-[42rem] lg:h-[40rem]">
            <CommunityFeed posts={posts} />
          </div>
        )}
      </div>
    </div>
  );
}
