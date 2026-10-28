import type { Metadata } from "next";
import Link from "next/link";
import { AGENCY } from "@/lib/agency";

export const metadata: Metadata = { title: "About" };

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 pt-10 pb-20">
      <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">About {AGENCY.name}</h1>
      <div className="prose prose-neutral mt-6 max-w-none">
        <p>{AGENCY.name} is a small demo travel agency. It exists to show a real booking system at work: live weather for thirteen South American capitals, tours with dated departures and limited seats, and a search that answers one question: which tours can I book between two dates, at an adventure level I am happy with?</p>
        <p>Nothing here is for sale. Bookings are test bookings made under a demo partner account and are cleared every night. The photos are made with an AI image model and show the mood of each place, not an exact view.</p>
        <h2>How the site works</h2>
        <ul>
          <li>Weather comes from OpenWeatherMap. A background job refreshes every city every fifteen minutes, so pages never wait for the weather service.</li>
          <li>Every tour has an adventure level from Relaxed to Tough. The level of a tour is the level of its hardest stop.</li>
          <li>Seats are counted live. Two people cannot book the last seat at the same time.</li>
        </ul>
        <p>The engineering behind it, with the architecture, the decisions and a live operations page, is in the <Link href="/case-study">case study</Link>.</p>
      </div>
    </div>
  );
}
