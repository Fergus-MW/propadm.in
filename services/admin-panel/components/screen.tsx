"use client";
import { Entities, EntityDetail } from "./screens/entities";
import { Overview, Documents, Search, Ingestion } from "./screens/knowledge";
import { GraphExplorer } from "./screens/graph";
import { Rules, Schema, Settings } from "./screens/configuration";
import { Actions, Communications } from "./screens/operations";
import { Header } from "./common";
import { Properties, Landlords, Unallocated } from "./screens/properties";
import { Providers } from "./screens/providers";
import Link from "next/link";
export function Screen({ route }: { route: string[] }) {
  const [section, id] = route;
  switch (section) {
    case undefined:
      return <Overview />;
    case "graph":
      return <GraphExplorer />;
    case "entities":
      return id ? <EntityDetail id={id} /> : <Entities />;
    case "properties":
      return <Properties id={id} />;
    case "landlords":
      return <Landlords id={id} />;
    case "providers":
      return <Providers id={id} />;
    case "unallocated":
      return <Unallocated />;
    case "tickets":
      return id ? <EntityDetail id={id} /> : <Entities tickets />;
    case "documents":
      return <Documents id={id} />;
    case "search":
      return <Search />;
    case "ingestion":
      return <Ingestion />;
    case "rules":
      return <Rules id={id} />;
    case "schema":
      return <Schema />;
    case "actions":
      return <Actions />;
    case "calls":
      return <Communications id={id} />;
    case "emails":
      return <Communications email />;
    case "settings":
      return <Settings />;
    default:
      return (
        <>
          <Header title="Page not found" />
          <Link href="/" className="draw-underline">
            Return to overview
          </Link>
        </>
      );
  }
}
