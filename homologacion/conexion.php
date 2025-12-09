<?php
// Configuración para PostgreSQL

function conectarBaseDatos() {
    $host = '192.168.1.100';  // nombre del servicio en docker-compose
    $dbname = 'data';
    $username = 'root';
    $password = '221910938';
    $port = 5432;  // Puerto por defecto de PostgreSQL
    try {
    // Conexión con PDO a PostgreSQL
    $pdo = new PDO("pgsql:host=$host;port=$port;dbname=$dbname", $username, $password);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    return $pdo;
    } catch (PDOException $e) {
        echo "<h2>❌ Error de conexión: " . $e->getMessage() . "</h2>";
        return null;
    }
}