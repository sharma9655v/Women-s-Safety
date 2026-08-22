import { Metadata } from "next";
import LandingContent from "./landing-content";

export const metadata: Metadata = {
  title: "Map for Women — Safety-Aware Navigation",
  description: "Plan safer routes, share journeys with guardians, and access emergency tools. Risk estimates — never a guarantee.",
};

export default function LandingPage() {
  return <LandingContent />;
}