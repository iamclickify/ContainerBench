const express = require("express");

const indexRoutes = require("./routes/index");
const healthRoutes = require("./routes/health");
const userRoutes = require("./routes/users");

const app = express();

const PORT = process.env.PORT || 3000;

// Middleware
app.use(express.json());

// Routes
app.use("/", indexRoutes);
app.use("/health", healthRoutes);
app.use("/users", userRoutes);

// Start server
app.listen(PORT, () => {
    console.log(`🚀 Express workload running on port ${PORT}`);
});