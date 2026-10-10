# Component system

Use `components/ui/` for controls and `components/library/` for reusable interface patterns. Props interfaces and inline prop types in each file are the canonical API. The original barrels are included; accordion, breadcrumb, carousel, button-group and hover-card also have direct file imports.

| Layer / file | Exported API |
| --- | --- |
| [Badge](../components/ui/Badge.tsx) | `Badge`, `StatusBadge` |
| [Button](../components/ui/Button.tsx) | `Button`, `buttonVariants` |
| [Card](../components/ui/Card.tsx) | `Card`, `CardAction`, `CardContent`, `CardDescription`, `CardFooter`, `CardHeader`, `CardTitle` |
| [Input](../components/ui/Input.tsx) | `FormInput`, `FormSelect`, `FormTextarea`, `Input` |
| [Markdown](../components/ui/Markdown.tsx) | `Markdown` |
| [Modal](../components/ui/Modal.tsx) | `Modal` |
| [ScrollFadeAffordance](../components/ui/ScrollFadeAffordance.tsx) | `useScrollFadeAffordance`, `ScrollFadeArrow` |
| [SearchSelect](../components/ui/SearchSelect.tsx) | `SearchSelect` |
| [Skeleton](../components/ui/Skeleton.tsx) | `Skeleton`, `SkeletonTable`, `SkeletonText` |
| [Table](../components/ui/Table.tsx) | `TableDensity`, `DataTable`, `Pagination`, `Table`, `TableBody`, `TableCaption`, `TableCell`, `TableFooter`, `TableHead`, `TableHeader`, `TableRow` |
| [TablePager](../components/ui/TablePager.tsx) | `TablePager` |
| [accordion](../components/ui/accordion.tsx) | `Accordion`, `AccordionContent`, `AccordionItem`, `AccordionTrigger` |
| [breadcrumb](../components/ui/breadcrumb.tsx) | `Breadcrumb`, `BreadcrumbEllipsis`, `BreadcrumbItem`, `BreadcrumbLink`, `BreadcrumbList`, `BreadcrumbPage`, `BreadcrumbSeparator` |
| [button-group](../components/ui/button-group.tsx) | `ButtonGroup`, `ButtonGroupSeparator`, `ButtonGroupText`, `buttonGroupVariants` |
| [carousel](../components/ui/carousel.tsx) | `Carousel`, `CarouselApi`, `CarouselContent`, `CarouselItem`, `CarouselNext`, `CarouselPrevious` |
| [chart](../components/ui/chart.tsx) | `ChartConfig`, `ChartContainer`, `ChartLegend`, `ChartLegendContent`, `ChartStyle`, `ChartTooltip`, `ChartTooltipContent` |
| [checkbox](../components/ui/checkbox.tsx) | `Checkbox` |
| [command](../components/ui/command.tsx) | `Command`, `CommandDialog`, `CommandEmpty`, `CommandGroup`, `CommandInput`, `CommandItem`, `CommandList`, `CommandSeparator`, `CommandShortcut` |
| [dialog](../components/ui/dialog.tsx) | `Dialog`, `DialogClose`, `DialogContent`, `DialogDescription`, `DialogFooter`, `DialogHeader`, `DialogOverlay`, `DialogPortal`, `DialogTitle`, `DialogTrigger` |
| [dropdown-menu](../components/ui/dropdown-menu.tsx) | `DropdownMenu`, `DropdownMenuCheckboxItem`, `DropdownMenuContent`, `DropdownMenuGroup`, `DropdownMenuItem`, `DropdownMenuLabel`, `DropdownMenuPortal`, `DropdownMenuRadioGroup`, `DropdownMenuRadioItem`, `DropdownMenuSeparator`, `DropdownMenuShortcut`, `DropdownMenuSub`, `DropdownMenuSubContent`, `DropdownMenuSubTrigger`, `DropdownMenuTrigger` |
| [hover-card](../components/ui/hover-card.tsx) | `HoverCard`, `HoverCardContent`, `HoverCardTrigger` |
| [input-group](../components/ui/input-group.tsx) | `InputGroup`, `InputGroupAddon`, `InputGroupButton`, `InputGroupInput`, `InputGroupText`, `InputGroupTextarea` |
| [label](../components/ui/label.tsx) | `Label` |
| [progress](../components/ui/progress.tsx) | `Progress` |
| [radio-group](../components/ui/radio-group.tsx) | `RadioGroup`, `RadioGroupItem` |
| [select](../components/ui/select.tsx) | `Select`, `SelectContent`, `SelectGroup`, `SelectItem`, `SelectLabel`, `SelectScrollDownButton`, `SelectScrollUpButton`, `SelectSeparator`, `SelectTrigger`, `SelectValue` |
| [separator](../components/ui/separator.tsx) | `Separator` |
| [sheet](../components/ui/sheet.tsx) | `Sheet`, `SheetClose`, `SheetContent`, `SheetDescription`, `SheetFooter`, `SheetHeader`, `SheetTitle`, `SheetTrigger` |
| [sidebar](../components/ui/sidebar.tsx) | `Sidebar`, `SidebarContent`, `SidebarFooter`, `SidebarGroup`, `SidebarGroupAction`, `SidebarGroupContent`, `SidebarGroupLabel`, `SidebarHeader`, `SidebarInput`, `SidebarInset`, `SidebarMenu`, `SidebarMenuAction`, `SidebarMenuBadge`, `SidebarMenuButton`, `SidebarMenuItem`, `SidebarMenuSkeleton`, `SidebarMenuSub`, `SidebarMenuSubButton`, `SidebarMenuSubItem`, `SidebarProvider`, `SidebarRail`, `SidebarSeparator`, `SidebarTrigger`, `useSidebar` |
| [tabs](../components/ui/tabs.tsx) | `Tabs`, `TabsContent`, `TabsList`, `TabsTrigger` |
| [textarea](../components/ui/textarea.tsx) | `Textarea` |
| [tooltip](../components/ui/tooltip.tsx) | `Tooltip`, `TooltipContent`, `TooltipProvider`, `TooltipTrigger` |
| [AccessDenied](../components/library/AccessDenied.tsx) | `AccessDenied` |
| [CodeBlock](../components/library/CodeBlock.tsx) | `CodeBlock` |
| [ConfirmDialog](../components/library/ConfirmDialog.tsx) | `ConfirmDialog` |
| [CopyField](../components/library/CopyField.tsx) | `useCopyToClipboard`, `CopyField` |
| [EmptyState](../components/library/EmptyState.tsx) | `EmptyState` |
| [ExternalLink](../components/library/ExternalLink.tsx) | `ExternalLink` |
| [FilterMenu](../components/library/FilterMenu.tsx) | `FilterOption`, `FilterMenu` |
| [InfoTip](../components/library/InfoTip.tsx) | `InfoTip` |
| [KeyValueGrid](../components/library/KeyValueGrid.tsx) | `KeyValue`, `KeyValueGrid` |
| [LoadError](../components/library/LoadError.tsx) | `LoadError` |
| [LoadMore](../components/library/LoadMore.tsx) | `LoadMore` |
| [Notice](../components/library/Notice.tsx) | `NoticeTone`, `Notice` |
| [OptionRow](../components/library/OptionRow.tsx) | `OptionList`, `OptionRow`, `RadioRow` |
| [OptionTile](../components/library/OptionTile.tsx) | `OPTION_TILE_CLASS`, `OptionTile` |
| [PageHeader](../components/library/PageHeader.tsx) | `PageHeader`, `SubpageHeader` |
| [RowMenu](../components/library/RowMenu.tsx) | `RowMenuItem`, `RowMenuControl`, `RowMenu` |
| [SearchInput](../components/library/SearchInput.tsx) | `SearchInput` |
| [SectionTabs](../components/library/SectionTabs.tsx) | `SectionTab`, `isSectionTabActive`, `SectionTabs` |
| [SelectionBar](../components/library/SelectionBar.tsx) | `SelectionBar`, `SelectionAction` |
| [SortableTableHead](../components/library/SortableTableHead.tsx) | `SortDirection`, `SortableTableHead` |
| [StatGrid](../components/library/StatGrid.tsx) | `Stat`, `StatGrid` |
| [StatusText](../components/library/StatusText.tsx) | `StatusTextVariant`, `statusTextClass`, `StatusText` |
| [Stepper](../components/library/Stepper.tsx) | `Step`, `Stepper` |
| [Surface](../components/library/Surface.tsx) | `Surface`, `SurfaceHeader` |
| [Tile](../components/library/Tile.tsx) | `Tile` |
| [ViewToggle](../components/library/ViewToggle.tsx) | `ViewToggle` |

## Shared conventions

- `Button`: ink primary; other action variants use the drawn line; `loading` shimmers.
- `Input`, `Textarea`, `SelectTrigger`, form fields and `InputGroup`: left rule.
- `Badge` / `StatusText`: ink words, status-coloured underline.
- `Card` / `Surface`: flat groups; add a heading only when needed.
- `Table` / `DataTable`: standard or dense, optional sticky headers. `TablePager` handles pagination.
- `Dialog` / `Modal`: one square dialog system. `ConfirmDialog` composes it for consequential actions.
- `Tabs` / `SectionTabs`: plain labels with the selected line.
- `Progress`: square ink fill, `active` shimmer.
- `RowMenu`, `SelectionBar`, `FilterMenu`, `SearchInput`: shared list controls.
- `OptionList`, `OptionRow`, `RadioRow`, `OptionTile`: shared selections.
- `styles.ts`: canonical left-rule, text-action, selection-line, caption, sticky-cell and divided-grid class constants.

Domain-specific job statuses and application shells are intentionally not pulled into the source kit. Define your own status union/map and render it through `StatusText`. The included `useIsMobile`, theme helpers, `plural`, `isPathActive` and date formatting utilities have no backend dependency.
