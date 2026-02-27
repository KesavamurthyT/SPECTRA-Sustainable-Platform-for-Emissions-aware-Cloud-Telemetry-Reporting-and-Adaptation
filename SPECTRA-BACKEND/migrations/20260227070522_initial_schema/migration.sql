-- CreateTable
CREATE TABLE "Region" (
    "code" TEXT NOT NULL PRIMARY KEY,
    "displayName" TEXT NOT NULL,
    "enabled" BOOLEAN NOT NULL DEFAULT true
);

-- CreateTable
CREATE TABLE "CarbonIntensityHour" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "regionCode" TEXT NOT NULL,
    "timestampUtc" DATETIME NOT NULL,
    "carbonIntensity" INTEGER NOT NULL,
    "rawRowJson" TEXT NOT NULL
);

-- CreateTable
CREATE TABLE "SimClock" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "simNowUtc" DATETIME NOT NULL,
    "updatedAt" DATETIME NOT NULL
);

-- CreateTable
CREATE TABLE "LatencyMetric" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "regionCode" TEXT NOT NULL,
    "timestampUtc" DATETIME NOT NULL,
    "latencyMs" REAL NOT NULL,
    "source" TEXT NOT NULL,
    "rawJson" TEXT NOT NULL
);

-- CreateTable
CREATE TABLE "Instance" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "name" TEXT NOT NULL,
    "regionCode" TEXT NOT NULL,
    "instanceType" TEXT NOT NULL,
    "costPerHour" REAL NOT NULL,
    "team" TEXT NOT NULL,
    "status" TEXT NOT NULL,
    "cpuUtilization" REAL NOT NULL DEFAULT 0,
    "memoryUtilization" REAL NOT NULL DEFAULT 0,
    "co2ePerMonth" REAL NOT NULL DEFAULT 0,
    "recommendedType" TEXT,
    "confidence" REAL,
    "potentialSavings" REAL,
    "costSavings" REAL,
    "risk" TEXT NOT NULL DEFAULT 'low'
);

-- CreateTable
CREATE TABLE "MigrationAction" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "fromRegion" TEXT NOT NULL,
    "toRegion" TEXT NOT NULL,
    "movedCount" INTEGER NOT NULL,
    "executedAtUtc" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- CreateTable
CREATE TABLE "Anomaly" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "instanceId" TEXT NOT NULL,
    "instanceName" TEXT NOT NULL,
    "detectedAtUtc" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "type" TEXT NOT NULL,
    "score" REAL NOT NULL,
    "expectedValue" REAL NOT NULL,
    "actualValue" REAL NOT NULL,
    "action" TEXT NOT NULL DEFAULT 'pending',
    "co2eSaved" REAL NOT NULL DEFAULT 0,
    "severity" TEXT NOT NULL
);

-- CreateTable
CREATE TABLE "TeamBudget" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "team" TEXT NOT NULL,
    "allocated" REAL NOT NULL,
    "used" REAL NOT NULL DEFAULT 0,
    "quarterYear" TEXT NOT NULL
);

-- CreateTable
CREATE TABLE "ScheduledJob" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "name" TEXT NOT NULL,
    "team" TEXT NOT NULL,
    "currentSchedule" TEXT NOT NULL,
    "recommendedSchedule" TEXT NOT NULL,
    "durationHours" REAL NOT NULL,
    "carbonSavings" REAL NOT NULL,
    "flexibility" TEXT NOT NULL,
    "accepted" BOOLEAN NOT NULL DEFAULT false
);

-- CreateTable
CREATE TABLE "Setting" (
    "key" TEXT NOT NULL PRIMARY KEY,
    "value" TEXT NOT NULL
);

-- CreateIndex
CREATE UNIQUE INDEX "TeamBudget_team_quarterYear_key" ON "TeamBudget"("team", "quarterYear");
