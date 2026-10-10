-- MySQL dump 10.13  Distrib 8.0.46, for Win64 (x86_64)
--
-- Host: localhost    Database: jb_ferramentas
-- ------------------------------------------------------
-- Server version	9.6.0-commercial

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `alugueis`
--

DROP TABLE IF EXISTS `alugueis`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `alugueis` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `data_devolucao` datetime DEFAULT NULL,
  `devolvido_em` datetime DEFAULT NULL,
  `valor_diario` decimal(10,2) NOT NULL DEFAULT '0.00',
  `taxa_atraso` decimal(10,2) NOT NULL DEFAULT '0.00',
  `id_servico` int unsigned NOT NULL,
  `criando_em` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `atualizado_em` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `id_servico` (`id_servico`),
  CONSTRAINT `alugueis_ibfk_1` FOREIGN KEY (`id_servico`) REFERENCES `servicos` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `estoque_minimo_filiais`
--

DROP TABLE IF EXISTS `estoque_minimo_filiais`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `estoque_minimo_filiais` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `quantidade_minima` int unsigned NOT NULL DEFAULT '0',
  `id_ferramenta` int unsigned NOT NULL,
  `id_filial` int unsigned NOT NULL,
  `criando_em` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `atualizado_em` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `id_ferramenta` (`id_ferramenta`),
  KEY `id_filial` (`id_filial`),
  CONSTRAINT `estoque_minimo_filiais_ibfk_1` FOREIGN KEY (`id_ferramenta`) REFERENCES `ferramentas` (`id`),
  CONSTRAINT `estoque_minimo_filiais_ibfk_2` FOREIGN KEY (`id_filial`) REFERENCES `filiais` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `estoque_pecas`
--

DROP TABLE IF EXISTS `estoque_pecas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `estoque_pecas` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `quantidade_atual` int unsigned NOT NULL DEFAULT '0',
  `quantidade_minima` int unsigned NOT NULL DEFAULT '0',
  `id_peca` int unsigned NOT NULL,
  `id_filial` int unsigned NOT NULL,
  `criando_em` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `atualizado_em` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `id_peca` (`id_peca`),
  KEY `id_filial` (`id_filial`),
  CONSTRAINT `estoque_pecas_ibfk_1` FOREIGN KEY (`id_peca`) REFERENCES `pecas` (`id`),
  CONSTRAINT `estoque_pecas_ibfk_2` FOREIGN KEY (`id_filial`) REFERENCES `filiais` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `ferramenta_tipos`
--

DROP TABLE IF EXISTS `ferramenta_tipos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ferramenta_tipos` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `tipo` varchar(100) NOT NULL,
  `criando_em` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `atualizado_em` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `tipo` (`tipo`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `ferramentas`
--

DROP TABLE IF EXISTS `ferramentas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ferramentas` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `marca` varchar(50) NOT NULL,
  `modelo` varchar(50) NOT NULL,
  `descricao` tinytext,
  `preco` decimal(10,2) NOT NULL DEFAULT '0.00',
  `tipo_oferta` enum('Comprar','Alugar') NOT NULL DEFAULT 'Comprar',
  `imagem` varchar(255) DEFAULT NULL,
  `id_ferramenta_tipo` int unsigned NOT NULL,
  `criando_em` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `atualizado_em` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `id_ferramenta_tipo` (`id_ferramenta_tipo`),
  CONSTRAINT `ferramentas_ibfk_1` FOREIGN KEY (`id_ferramenta_tipo`) REFERENCES `ferramenta_tipos` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `filiais`
--

DROP TABLE IF EXISTS `filiais`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `filiais` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `codigo_filial` varchar(10) NOT NULL,
  `nome` varchar(100) NOT NULL,
  `endereco` varchar(200) NOT NULL,
  `criando_em` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `atualizado_em` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `codigo_filial` (`codigo_filial`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `manutencao_pecas`
--

DROP TABLE IF EXISTS `manutencao_pecas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `manutencao_pecas` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `quantidade` int unsigned NOT NULL DEFAULT '1',
  `id_manutencao` int unsigned NOT NULL,
  `id_estoque_peca` int unsigned NOT NULL,
  `criando_em` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `atualizado_em` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `id_manutencao` (`id_manutencao`),
  KEY `id_estoque_peca` (`id_estoque_peca`),
  CONSTRAINT `manutencao_pecas_ibfk_1` FOREIGN KEY (`id_manutencao`) REFERENCES `manutencoes` (`id`),
  CONSTRAINT `manutencao_pecas_ibfk_2` FOREIGN KEY (`id_estoque_peca`) REFERENCES `estoque_pecas` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `manutencoes`
--

DROP TABLE IF EXISTS `manutencoes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `manutencoes` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `diagnostico` text NOT NULL,
  `garantia` int NOT NULL,
  `foto_equipamento` varchar(255) DEFAULT NULL,
  `id_servico` int unsigned NOT NULL,
  `criando_em` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `atualizado_em` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `id_servico` (`id_servico`),
  CONSTRAINT `manutencoes_ibfk_1` FOREIGN KEY (`id_servico`) REFERENCES `servicos` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `pecas`
--

DROP TABLE IF EXISTS `pecas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `pecas` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `codigo_barras` varchar(20) NOT NULL,
  `nome` varchar(100) NOT NULL,
  `fabricante` varchar(100) NOT NULL,
  `custo` decimal(10,2) NOT NULL DEFAULT '0.00',
  `preco_venda` decimal(10,2) NOT NULL DEFAULT '0.00',
  `criando_em` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `atualizado_em` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `codigo_barras` (`codigo_barras`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `perfis`
--

DROP TABLE IF EXISTS `perfis`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `perfis` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `perfil` varchar(20) NOT NULL,
  `descricao` text,
  `ativo` tinyint(1) NOT NULL DEFAULT '1',
  `criando_em` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `atualizado_em` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_perfis_perfil` (`perfil`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `pessoas`
--

DROP TABLE IF EXISTS `pessoas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `pessoas` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `nome` varchar(100) NOT NULL,
  `tipo` enum('pf','pj') NOT NULL DEFAULT 'pf',
  `endereco` varchar(200) NOT NULL,
  `email` varchar(100) NOT NULL,
  `telefone` varchar(20) NOT NULL,
  `criando_em` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `atualizado_em` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `codigo` varchar(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_pessoas_codigo` (`codigo`)
) ENGINE=InnoDB AUTO_INCREMENT=31 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `saude_unidade_ferramentas`
--

DROP TABLE IF EXISTS `saude_unidade_ferramentas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `saude_unidade_ferramentas` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `avaliacao` varchar(100) DEFAULT NULL,
  `id_unidade_ferramenta` int unsigned NOT NULL,
  `criando_em` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `atualizado_em` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `id_unidade_ferramenta` (`id_unidade_ferramenta`),
  CONSTRAINT `saude_unidade_ferramentas_ibfk_1` FOREIGN KEY (`id_unidade_ferramenta`) REFERENCES `unidade_ferramentas` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `servico_ferramentas`
--

DROP TABLE IF EXISTS `servico_ferramentas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `servico_ferramentas` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `id_servico` int unsigned NOT NULL,
  `id_unidade_ferramenta` int unsigned NOT NULL,
  PRIMARY KEY (`id`),
  KEY `id_servico` (`id_servico`),
  KEY `id_unidade_ferramenta` (`id_unidade_ferramenta`),
  CONSTRAINT `servico_ferramentas_ibfk_1` FOREIGN KEY (`id_servico`) REFERENCES `servicos` (`id`),
  CONSTRAINT `servico_ferramentas_ibfk_2` FOREIGN KEY (`id_unidade_ferramenta`) REFERENCES `unidade_ferramentas` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=17 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `servico_historicos`
--

DROP TABLE IF EXISTS `servico_historicos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `servico_historicos` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `titulo` varchar(200) NOT NULL,
  `descricao_atividade` text,
  `tempo_execucao_minutos` int unsigned DEFAULT NULL,
  `id_servico` int unsigned NOT NULL,
  `id_filial` int unsigned NOT NULL,
  `id_pessoa_responsavel` int unsigned NOT NULL,
  `id_servico_status_lista` int unsigned NOT NULL,
  `criando_em` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `atualizado_em` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `id_servico` (`id_servico`),
  KEY `id_filial` (`id_filial`),
  KEY `id_pessoa_responsavel` (`id_pessoa_responsavel`),
  KEY `id_servico_status_lista` (`id_servico_status_lista`),
  CONSTRAINT `servico_historicos_ibfk_1` FOREIGN KEY (`id_servico`) REFERENCES `servicos` (`id`),
  CONSTRAINT `servico_historicos_ibfk_2` FOREIGN KEY (`id_filial`) REFERENCES `filiais` (`id`),
  CONSTRAINT `servico_historicos_ibfk_3` FOREIGN KEY (`id_pessoa_responsavel`) REFERENCES `pessoas` (`id`),
  CONSTRAINT `servico_historicos_ibfk_4` FOREIGN KEY (`id_servico_status_lista`) REFERENCES `servico_status_listas` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `servico_status_listas`
--

DROP TABLE IF EXISTS `servico_status_listas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `servico_status_listas` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `tipo_servico` enum('manutencao','aluguel','venda') NOT NULL,
  `status` varchar(20) NOT NULL,
  `ativo` tinyint(1) NOT NULL DEFAULT '1',
  `criando_em` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `atualizado_em` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `servicos`
--

DROP TABLE IF EXISTS `servicos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `servicos` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `servico_solicitado` enum('manutencao','aluguel','venda') NOT NULL,
  `titulo_servico` varchar(200) NOT NULL,
  `descricao_servico` text NOT NULL,
  `data_abertura` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `valor_servico` decimal(10,2) NOT NULL DEFAULT '0.00',
  `status_servico` varchar(50) NOT NULL DEFAULT 'Aberto',
  `pagamento` varchar(20) DEFAULT NULL,
  `id_pessoa_solicitante` int unsigned NOT NULL,
  `id_pessoa_abertura` int unsigned NOT NULL,
  `criando_em` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `atualizado_em` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `id_pessoa_solicitante` (`id_pessoa_solicitante`),
  KEY `id_pessoa_abertura` (`id_pessoa_abertura`),
  CONSTRAINT `servicos_ibfk_1` FOREIGN KEY (`id_pessoa_solicitante`) REFERENCES `pessoas` (`id`),
  CONSTRAINT `servicos_ibfk_2` FOREIGN KEY (`id_pessoa_abertura`) REFERENCES `pessoas` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=41 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `unidade_ferramentas`
--

DROP TABLE IF EXISTS `unidade_ferramentas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `unidade_ferramentas` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `numero_serie` varchar(50) DEFAULT NULL,
  `id_ferramenta` int unsigned NOT NULL,
  `id_filial` int unsigned NOT NULL,
  `status` enum('em_estoque','alugada','manutencao','reservada','baixada') NOT NULL DEFAULT 'em_estoque',
  `criando_em` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `atualizado_em` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `numero_serie` (`numero_serie`),
  KEY `id_ferramenta` (`id_ferramenta`),
  KEY `id_filial` (`id_filial`),
  CONSTRAINT `unidade_ferramentas_ibfk_1` FOREIGN KEY (`id_ferramenta`) REFERENCES `ferramentas` (`id`),
  CONSTRAINT `unidade_ferramentas_ibfk_2` FOREIGN KEY (`id_filial`) REFERENCES `filiais` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=17 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `usuarios`
--

DROP TABLE IF EXISTS `usuarios`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `usuarios` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `nome_usuario` varchar(100) NOT NULL,
  `senha` varchar(100) NOT NULL,
  `id_pessoa` int unsigned NOT NULL,
  `id_perfil` int unsigned NOT NULL,
  `ativo` tinyint(1) NOT NULL DEFAULT '1',
  `criando_em` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `atualizado_em` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `nome_usuario` (`nome_usuario`),
  KEY `id_pessoa` (`id_pessoa`),
  KEY `id_perfil` (`id_perfil`),
  CONSTRAINT `usuarios_ibfk_1` FOREIGN KEY (`id_pessoa`) REFERENCES `pessoas` (`id`),
  CONSTRAINT `usuarios_ibfk_2` FOREIGN KEY (`id_perfil`) REFERENCES `perfis` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-10-10 11:31:26
