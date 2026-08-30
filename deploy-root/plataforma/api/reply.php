<?php
declare(strict_types=1); require_once __DIR__ . '/../auth.php'; require_role('victor'); require_csrf();
$data=json_decode(file_get_contents('php://input'),true) ?: $_POST; $phone=trim((string)($data['phone']??'')); $text=trim((string)($data['content']??''));
if (!preg_match('/^\+?[0-9]{8,20}$/',$phone)||$text==='') json_response(['error'=>'Datos invalidos'],422);
$cfg=app_config(); $body=json_encode(['messaging_product'=>'whatsapp','to'=>$phone,'type'=>'text','text'=>['body'=>$text]]);
$ch=curl_init('https://graph.facebook.com/v21.0/'.$cfg['meta_phone_id'].'/messages'); curl_setopt_array($ch,[CURLOPT_POST=>true,CURLOPT_POSTFIELDS=>$body,CURLOPT_HTTPHEADER=>['Authorization: Bearer '.$cfg['meta_token'],'Content-Type: application/json'],CURLOPT_RETURNTRANSFER=>true,CURLOPT_TIMEOUT=>15]); $result=curl_exec($ch); $code=curl_getinfo($ch,CURLINFO_HTTP_CODE); curl_close($ch);
if ($code<200||$code>=300) json_response(['error'=>'Meta no acepto el mensaje'],502);
$stmt=db()->prepare('INSERT INTO conversations(phone,role,content) VALUES(?,?,?)'); $stmt->execute([$phone,'assistant',$text]); json_response(['status'=>'ok']);
