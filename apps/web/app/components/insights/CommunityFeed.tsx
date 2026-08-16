"use client";

import { MessageSquare, ShieldCheck, Timer } from "lucide-react";
import { Badge } from "@/app/components/ui/Badge";
import { Card, CardHeader } from "@/app/components/ui/Card";
import { timeAgo } from "@/lib/format";
import type { CommunityPost } from "@/lib/types";

function PostCard({ post }: { post: CommunityPost }) {
  return (
    <div className="flex gap-3 rounded-xl border border-border bg-surface p-3 transition-colors duration-200 hover:border-border-glow hover:bg-surface-hover">
      <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
        <MessageSquare className="size-4" aria-hidden />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5">
          <Badge
            tone={
              post.kind === "alert" ? "danger" : post.kind === "route_update" ? "success" : "info"
            }
          >
            {post.kind.replace(/_/g, " ")}
          </Badge>
          {post.status === "VERIFIED" ? (
            <span className="flex items-center gap-0.5 text-[10px] font-medium text-info">
              <ShieldCheck className="size-3" aria-hidden /> Verified
            </span>
          ) : (
            <span className="text-[10px] text-text-muted">Pending review</span>
          )}
        </div>
        <p className="mt-1 text-xs text-text-secondary leading-relaxed">{post.text}</p>
        <div className="mt-1.5 flex items-center gap-3 text-[10px] text-text-muted">
          <span>{post.location}</span>
          <span className="flex items-center gap-0.5">
            <Timer className="size-3" aria-hidden /> {timeAgo(post.created_at)}
          </span>
        </div>
      </div>
    </div>
  );
}

export function CommunityFeed({ posts }: { posts: CommunityPost[] }) {
  return (
    <Card className="flex h-full flex-col">
      <CardHeader title="Community Feed" subtitle="Anonymous updates — authorship is never shown" />
      {posts.length === 0 ? (
        <p className="py-6 text-center text-xs text-text-muted">No community posts yet.</p>
      ) : (
        <div className="flex-1 space-y-2 overflow-y-auto">
          {posts.map((post) => (
            <PostCard key={post.id} post={post} />
          ))}
        </div>
      )}
    </Card>
  );
}
