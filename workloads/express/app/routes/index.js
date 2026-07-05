const express = require("express");

const router = express.Router();

router.get("/", (req, res) => {
    res.json({
        project: "ContainerBench",
        workload: "Express",
        status: "running"
    });
});

module.exports = router;