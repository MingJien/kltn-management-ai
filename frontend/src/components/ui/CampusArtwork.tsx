/** Original symbolic SVG campus & lotus artwork for DThU Academic Blue V3.
 *  Strictly decorative (aria-hidden) — never replaces official crest /assets/dthu-logo.png
 *  and never claims to be a photographic depiction of a specific building. */

export function CampusBannerArt({ className = "" }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 420 220"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      focusable="false"
    >
      {/* Clean academic drafting coordinates */}
      <g stroke="#246B96" strokeOpacity="0.13" strokeWidth="1">
        <path d="M44 34H396M44 74H396M44 114H396M44 154H396M44 194H396" />
        <path d="M110 18V208M178 18V208M246 18V208M314 18V208M382 18V208" />
      </g>

      {/* Soft sunlit lotus aura & radial halo */}
      <circle cx="294" cy="94" r="76" fill="#EAF4FB" fillOpacity="0.58" />
      <circle cx="294" cy="94" r="52" stroke="#1976B8" strokeOpacity="0.14" strokeWidth="1" strokeDasharray="4 4" />

      {/* Blooming Dong Thap Lotus silhouette (layered petals) */}
      <g stroke="#1976B8" strokeOpacity="0.26" strokeWidth="1.35" strokeLinecap="round" strokeLinejoin="round">
        <path d="M276 92C276 62 294 42 294 42C294 42 312 62 312 92C312 106 304 116 294 116C284 116 276 106 276 92Z" fill="#EAF4FB" fillOpacity="0.55" />
        <path d="M258 106C248 80 262 56 262 56C262 56 282 70 288 98" />
        <path d="M330 106C340 80 326 56 326 56C326 56 306 70 300 98" />
        <path d="M242 114C224 98 225 72 225 72C225 72 252 76 272 102" />
        <path d="M346 114C364 98 363 72 363 72C363 72 336 76 316 102" />
      </g>

      {/* Architectural DThU academic lecture hall facade */}
      <g stroke="#174A6D" strokeOpacity="0.28" strokeWidth="1.45" strokeLinejoin="round">
        <path d="M122 194H404" />
        <path d="M138 194V186H388V194" fill="#EAF4FB" fillOpacity="0.45" />
        {/* Main pediment wing */}
        <path d="M160 186V112L236 78L312 112V186" fill="#FFFFFF" fillOpacity="0.65" />
        <path d="M170 116H302" />
        <path d="M180 186V124M208 186V118M236 186V110M264 186V118M292 186V124" />
        {/* Facade rhythm windows */}
        <rect x="224" y="138" width="24" height="48" rx="12" fill="#EAF4FB" fillOpacity="0.7" />
        {/* Side academic library pavilion */}
        <path d="M312 128H378V186H312" fill="#FFFFFF" fillOpacity="0.55" />
        <path d="M328 142H344V158H328ZM354 142H370V158H354ZM328 166H344V186H328ZM354 166H370V186H354Z" />
        {/* Stylised campus trees */}
        <path d="M136 186V162M136 164C126 164 122 154 128 148C132 142 142 142 146 149C151 156 146 164 136 164Z" />
        <path d="M392 186V166M392 168C384 168 380 159 385 154C389 149 397 149 401 155C405 161 400 168 392 168Z" />
      </g>

      {/* Subtle Academic Gold Mekong flow & focal points */}
      <path d="M104 172C180 150 264 186 404 158" stroke="#D7A348" strokeOpacity="0.52" strokeWidth="1.5" strokeLinecap="round" />
      <circle cx="236" cy="78" r="3.4" fill="#D7A348" fillOpacity="0.65" />
      <circle cx="294" cy="42" r="2.8" fill="#D7A348" fillOpacity="0.62" />
    </svg>
  );
}

export function SidebarLotusArt({ className = "" }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 264 164"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      focusable="false"
    >
      {/* Subtle architectural compass arc */}
      <circle cx="206" cy="64" r="56" stroke="#D6E6F3" strokeOpacity="0.1" strokeWidth="1" strokeDasharray="3 4" />
      <circle cx="206" cy="64" r="36" stroke="#D6E6F3" strokeOpacity="0.12" strokeWidth="1" />

      {/* Mekong river horizon waves */}
      <path d="M0 132C58 112 128 144 264 114" stroke="#D6E6F3" strokeOpacity="0.18" strokeWidth="1.15" />
      <path d="M0 148C78 128 158 158 264 134" stroke="#D7A348" strokeOpacity="0.28" strokeWidth="1.1" />

      {/* Layered DThU Lecture Hall architectural line-art on left/center */}
      <g stroke="#D6E6F3" strokeOpacity="0.22" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M16 142H172" />
        <path d="M26 142V96L74 74L122 96V142" fill="#FFFFFF" fillOpacity="0.04" />
        <path d="M36 98H112" />
        <path d="M44 142V104M62 142V100M86 142V100M104 142V104" />
        <path d="M68 142V118C68 114 80 114 80 118V142" />
        <path d="M122 106H160V142" />
        <path d="M132 115H142V125H132ZM147 115H155V125H147Z" />
      </g>

      {/* Multi-petal Dong Thap Lotus fine line-art on right */}
      <g stroke="#E3F1FA" strokeOpacity="0.28" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round">
        <path d="M192 92C192 64 206 46 206 46C206 46 220 64 220 92C220 103 214 110 206 110C198 110 192 103 192 92Z" fill="#FFFFFF" fillOpacity="0.05" />
        <path d="M175 102C166 78 179 58 179 58C179 58 197 70 201 94" />
        <path d="M237 102C246 78 233 58 233 58C233 58 215 70 211 94" />
        <path d="M160 110C146 95 148 73 148 73C148 73 171 78 187 99" />
        <path d="M252 110C262 98 261 78 261 74C250 77 234 86 225 99" />
      </g>

      {/* Academic Gold horizon & crest points */}
      <circle cx="74" cy="74" r="2.2" fill="#D7A348" fillOpacity="0.55" />
      <circle cx="206" cy="46" r="2.5" fill="#D7A348" fillOpacity="0.65" />
    </svg>
  );
}

export function LoginCampusArt({ className = "" }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 800 900"
      preserveAspectRatio="xMidYMid slice"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      focusable="false"
    >
      {/* Subtle architectural grid */}
      <g stroke="#D6E6F3" strokeOpacity="0.08" strokeWidth="1">
        <path d="M0 160H800M0 320H800M0 480H800M0 640H800M0 800H800" />
        <path d="M160 0V900M320 0V900M480 0V900M640 0V900" />
      </g>

      {/* Architectural arcs & geometry */}
      <circle cx="670" cy="140" r="210" stroke="#D6E6F3" strokeOpacity="0.11" strokeWidth="1.5" />
      <circle cx="670" cy="140" r="145" stroke="#D6E6F3" strokeOpacity="0.09" strokeWidth="1" strokeDasharray="6 6" />
      <circle cx="110" cy="790" r="240" stroke="#D6E6F3" strokeOpacity="0.1" strokeWidth="1.5" />

      {/* Symbolic DThU lotus & colonnade facade */}
      <g stroke="#E3F1FA" strokeOpacity="0.17" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
        <path d="M460 900V740L595 680L730 740V900" fill="#FFFFFF" fillOpacity="0.03" />
        <path d="M498 900V762M546 900V748M595 900V736M644 900V748M692 900V762" />
        <path d="M482 750H708" />
        <path d="M565 654C565 610 595 576 595 576C595 576 625 610 625 654C625 672 612 686 595 686C578 686 565 672 565 654Z" />
        <path d="M538 670C522 632 544 594 544 594C544 594 575 616 584 660" />
        <path d="M652 670C668 632 646 594 646 594C646 594 615 616 606 660" />
      </g>

      {/* Academic Gold knowledge flow curves */}
      <path d="M-20 710C180 650 360 760 820 670" stroke="#D7A348" strokeOpacity="0.4" strokeWidth="1.6" />
      <circle cx="595" cy="576" r="4" fill="#D7A348" fillOpacity="0.65" />
      <circle cx="320" cy="696" r="3" fill="#D7A348" fillOpacity="0.52" />
    </svg>
  );
}

export function AiKnowledgeArt({ className = "" }: { className?: string }) {
  return (
    <svg
      className={className}
      width="176"
      height="88"
      viewBox="0 0 176 88"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      focusable="false"
    >
      {/* Document & citation network graph (scholarly, no cartoon robot) */}
      <path d="M26 58L68 24L118 46L154 22" stroke="#1976B8" strokeOpacity="0.38" strokeWidth="1.5" />
      <path d="M68 24L84 68L118 46" stroke="#246B96" strokeOpacity="0.32" strokeWidth="1.4" strokeDasharray="3 3" />
      <rect x="14" y="44" width="24" height="30" rx="4" fill="#EAF4FB" stroke="#1976B8" strokeOpacity="0.55" strokeWidth="1.3" />
      <path d="M20 53H32M20 59H30M20 65H27" stroke="#1976B8" strokeOpacity="0.7" strokeWidth="1.3" strokeLinecap="round" />
      <rect x="56" y="10" width="24" height="30" rx="4" fill="#FFFFFF" stroke="#1976B8" strokeOpacity="0.75" strokeWidth="1.3" />
      <path d="M62 19H74M62 25H72M62 31H69" stroke="#174A6D" strokeOpacity="0.75" strokeWidth="1.3" strokeLinecap="round" />
      <rect x="106" y="34" width="24" height="30" rx="4" fill="#EAF4FB" stroke="#246B96" strokeOpacity="0.65" strokeWidth="1.3" />
      <path d="M112 43H124M112 49H122M112 55H119" stroke="#174A6D" strokeOpacity="0.7" strokeWidth="1.3" strokeLinecap="round" />
      <circle cx="154" cy="22" r="9" fill="#FFF7E8" stroke="#D7A348" strokeWidth="1.4" />
      <circle cx="154" cy="22" r="3.5" fill="#D7A348" />
      <circle cx="84" cy="68" r="5" fill="#E3F1FA" stroke="#1976B8" strokeWidth="1.3" />
    </svg>
  );
}
